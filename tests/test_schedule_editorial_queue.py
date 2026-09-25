import unittest
import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace
from datetime import datetime
from scripts import editorial_queue as queue
from scripts import schedule_editorial_queue as scheduler
from scripts import fill_editorial_schedule as filler
from scripts.schedule_editorial_queue import next_slot


class ScheduleSlotTests(unittest.TestCase):
    def test_tomorrow_ten_korean_time(self):
        now = datetime(2026, 9, 20, 16, tzinfo=queue.KST)
        self.assertEqual(next_slot([], now).isoformat(), '2026-09-21T10:00:00+09:00')

    def test_skips_occupied_future_day(self):
        now = datetime(2026, 9, 20, 16, tzinfo=queue.KST)
        posts = [{'status':'future', 'date_gmt':'2026-09-21T01:00:00'}]
        self.assertEqual(next_slot(posts, now).day, 22)

    def test_unknown_date_fails_closed(self):
        with self.assertRaises(ValueError):
            next_slot([{'status':'future'}], datetime(2026, 9, 20, 16, tzinfo=queue.KST))

    def test_full_week_returns_none(self):
        posts = [{'status':'future','date_gmt':f'2026-09-{day}T01:00:00'} for day in range(21,28)]
        self.assertIsNone(next_slot(posts, datetime(2026,9,20,16,tzinfo=queue.KST)))

    def test_any_published_post_occupies_whole_korean_day(self):
        posts = [{'status': 'publish', 'date_gmt': '2026-09-20T23:30:00Z'}]
        self.assertEqual(next_slot(posts, datetime(2026,9,20,16,tzinfo=queue.KST)).day, 22)


class ScheduleSafetyTests(unittest.TestCase):
    """Synthetic approvals/results only; no real publisher or REST calls."""
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.now = datetime(2026,9,20,16,tzinfo=queue.KST)
        self.inventory = self.root/'inventory.json'
        self.inventory.write_text(json.dumps({'metadata': {'statuses': {'publish':0,'draft':0,'future':0}}, 'posts': []}))
        self.client = Mock()
        self.publisher = Mock(return_value={'post_id':999,'status':'scheduled','content_verified':True})
        for target, values in (
            ('ROOT', {'new': self.root}),
            ('WordPressClient', {'return_value': self.client}),
            ('configure_logger', {'return_value': Mock()}),
            ('publish_prepared_topic', {'new': self.publisher}),
        ):
            p=patch.object(scheduler,target,**values);p.start();self.addCleanup(p.stop)
        for target, values in (
            ('scripts.schedule_editorial_queue.WordPressConfig.from_environment', {'return_value': Mock()}),
            ('scripts.schedule_editorial_queue.deep.refresh_inventory', {'return_value': self.inventory}),
            ('scripts.schedule_editorial_queue.queue.preflight', {'return_value': SimpleNamespace()}),
            ('scripts.schedule_editorial_queue.queue.review_fresh_context', {'return_value': {'verdict':'APPROVED'}}),
            ('scripts.schedule_editorial_queue.queue.clock', {'return_value': self.now}),
        ):
            p=patch(target,**values);p.start();self.addCleanup(p.stop)

    def add_row(self):
        queue.directory(self.root).mkdir(parents=True)
        self.path=queue.directory(self.root)/'fixture.json'
        queue.save(self.path, {'schema_version':1,'queue_id':'fixture','status':'queued','prepared_at':self.now.isoformat(),'candidate':{'candidate_id':'fixture'},'prepared':{}}, new=True)

    def test_unknown_publisher_failure_persists_barrier_and_never_retries(self):
        self.add_row();self.publisher.side_effect=TimeoutError('synthetic response lost')
        with self.assertRaises(TimeoutError): scheduler.schedule_one()
        self.assertEqual(json.loads(self.path.read_text())['status'],'publishing')
        with self.assertRaisesRegex(ValueError,'reconciliation'): scheduler.schedule_one()
        self.publisher.assert_called_once()

    def test_review_hold_is_not_retried_each_timer_tick(self):
        self.add_row()
        with patch.object(queue,'review_fresh_context',side_effect=ValueError('review_hold')) as review:
            with self.assertRaises(ValueError): scheduler.schedule_one()
            self.assertEqual(json.loads(self.path.read_text())['status'],'held')
            self.assertEqual(scheduler.schedule_one()['status'],'no_approved_article')
            review.assert_called_once()
        self.publisher.assert_not_called()

    def test_failed_future_body_confirmation_blocks_retry(self):
        self.add_row();self.publisher.return_value['content_verified']=False
        with self.assertRaisesRegex(ValueError,'reconciliation'): scheduler.schedule_one()
        row=json.loads(self.path.read_text())
        self.assertEqual(row['publication']['post_id'],999)
        self.assertEqual(row['status'],'publishing')
        with self.assertRaisesRegex(ValueError,'reconciliation'): scheduler.schedule_one()
        self.publisher.assert_called_once()

    def test_publisher_date_verification_exception_blocks_retry(self):
        self.add_row();self.publisher.side_effect=ValueError('scheduled_date_mismatch')
        with self.assertRaisesRegex(ValueError,'date_mismatch'): scheduler.schedule_one()
        with self.assertRaisesRegex(ValueError,'reconciliation'): scheduler.schedule_one()
        self.publisher.assert_called_once()

    def test_wrong_returned_date_persists_barrier_after_confirmed_write(self):
        self.add_row()
        self.publisher.return_value.update(date='2026-09-21T11:00:00', date_gmt='2026-09-21T02:00:00')
        with self.assertRaisesRegex(ValueError,'date_mismatch'): scheduler.schedule_one()
        self.assertEqual(json.loads(self.path.read_text())['status'],'publishing')
        with self.assertRaisesRegex(ValueError,'reconciliation'): scheduler.schedule_one()
        self.publisher.assert_called_once()

    def test_missing_future_snapshot_never_calls_publisher(self):
        self.add_row()
        self.inventory.write_text(json.dumps({'metadata':{'statuses':{'publish':0,'draft':0}},'posts':[]}))
        with self.assertRaisesRegex(ValueError,'missing_future'): scheduler.schedule_one()
        self.publisher.assert_not_called()

    def test_cli_owns_lane_lock_around_call(self):
        events=[];lock=Mock()
        lock.acquire.side_effect=lambda:events.append('acquire')
        lock.release.side_effect=lambda:events.append('release')
        with patch.object(scheduler.deep,'PipelineLock',return_value=lock), patch.object(scheduler,'schedule_one',side_effect=lambda:events.append('schedule') or {}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scheduler.main(),0)
        self.assertEqual(events,['acquire','schedule','release'])

    def test_lock_failure_never_enters_scheduler(self):
        lock=Mock();lock.acquire.side_effect=RuntimeError('locked')
        with patch.object(scheduler.deep,'PipelineLock',return_value=lock), patch.object(scheduler,'schedule_one') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scheduler.main(),1)
        run.assert_not_called()

    def test_known_busy_lock_defers_without_publishing(self):
        lock=Mock();lock.acquire.side_effect=scheduler.deep.PipelineError('Daily Pipeline lock is already held')
        output=io.StringIO()
        with patch.object(scheduler.deep,'PipelineLock',return_value=lock), patch.object(scheduler,'schedule_one') as run, contextlib.redirect_stdout(output):
            self.assertEqual(scheduler.main(),0)
        self.assertEqual(json.loads(output.getvalue())['status'],'deferred')
        run.assert_not_called()


class FillSafetyTests(unittest.TestCase):
    def test_stops_immediately_on_schedule_failure(self):
        with patch.object(filler.subprocess,'run',return_value=SimpleNamespace(returncode=1)) as run:
            self.assertEqual(filler.main(),1)
        run.assert_called_once()

    def test_stops_on_preparation_failure(self):
        with patch.object(filler.subprocess,'run',side_effect=[SimpleNamespace(returncode=0),SimpleNamespace(returncode=2)]) as run, patch.object(queue,'preparation_allowed',return_value=True),patch.object(queue,'rows',return_value=[]):
            self.assertEqual(filler.main(),2)
        self.assertEqual(run.call_count,2)

    def _run_writer(self, runs, error_type, **extra):
        def run(command, cwd):
            if '--prepare-only' in command:
                directory = runs / f'20260925T00000{len(list(runs.iterdir()))}Z-x'
                directory.mkdir()
                (directory / 'result.json').write_text(json.dumps(
                    {'failed': True, 'error_type': error_type, 'wordpress_write_count': 0, **extra}))
                return SimpleNamespace(returncode=1)
            return SimpleNamespace(returncode=0)
        return run

    def test_reviewer_rejection_moves_to_next_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            with patch.object(filler, 'RUNS', runs), \
                    patch.object(filler.subprocess, 'run', side_effect=self._run_writer(runs, 'ContentQualityRejection')) as run, \
                    patch.object(queue, 'preparation_allowed', return_value=True), patch.object(queue, 'rows', return_value=[]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(filler.main(), 0)
        preparations = [c for c in run.call_args_list if '--prepare-only' in c.args[0]]
        self.assertEqual(len(preparations), 7)

    def test_editorial_gate_rejection_moves_to_next_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            writer = self._run_writer(runs, 'ValueError', reason='editorial_gate_rejected')
            with patch.object(filler, 'RUNS', runs), patch.object(filler.subprocess, 'run', side_effect=writer) as run, \
                    patch.object(queue, 'preparation_allowed', return_value=True), patch.object(queue, 'rows', return_value=[]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(filler.main(), 0)
        self.assertEqual(len([c for c in run.call_args_list if '--prepare-only' in c.args[0]]), 7)

    def test_other_value_error_still_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            with patch.object(filler, 'RUNS', runs), \
                    patch.object(filler.subprocess, 'run', side_effect=self._run_writer(runs, 'ValueError')) as run, \
                    patch.object(queue, 'preparation_allowed', return_value=True), patch.object(queue, 'rows', return_value=[]):
                self.assertEqual(filler.main(), 1)
        self.assertEqual(run.call_count, 2)

    def test_non_review_failure_still_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            with patch.object(filler, 'RUNS', runs), \
                    patch.object(filler.subprocess, 'run', side_effect=self._run_writer(runs, 'DiscoveryError')) as run, \
                    patch.object(queue, 'preparation_allowed', return_value=True), patch.object(queue, 'rows', return_value=[]):
                self.assertEqual(filler.main(), 1)
        self.assertEqual(run.call_count, 2)

    def test_never_prepares_more_than_seven(self):
        snapshots=[]
        for n in range(7): snapshots.extend([list(range(n)),list(range(n+1))])
        with patch.object(filler.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run, patch.object(queue,'preparation_allowed',return_value=True),patch.object(queue,'rows',side_effect=snapshots):
            self.assertEqual(filler.main(),0)
        preparations=[c for c in run.call_args_list if '--prepare-only' in c.args[0]]
        self.assertEqual(len(preparations),7)

    def test_no_new_approved_row_stops_refill(self):
        with patch.object(filler.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run, patch.object(queue,'preparation_allowed',return_value=True),patch.object(queue,'rows',return_value=[]),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(filler.main(),0)
        self.assertEqual(run.call_count,2)
