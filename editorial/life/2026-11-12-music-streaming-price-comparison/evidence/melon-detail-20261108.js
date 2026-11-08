// https://www.melon.com/resource/script/web/cm/melonweb_cm_detail.js?ts=20241107 (curl 2026-11-08)
var obj = [
    // 0 = 스트리밍플러스
    {
        title: "스트리밍 플러스란?",
        text: "온라인과 오프라인에서 무제한 듣기가 가능한 이용권입니다. 오프라인 파일의 저장 및 재생은 인증된 모바일 디바이스 1대에서 가능하며, 오프라인 재생 기능을 통해 데이터 연결 없이 음악을 감상할 수 있습니다.",
        label: ['무제한 듣기', '오프라인 재생'],
        data: [
            [true, false],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 1 = fi-hi 스트리밍 클럽
    {
        title: "Hi-Fi 스트리밍 클럽이란?",
        text: "무손실 고음질 음원파일(FLAC)을 무제한으로 들을 수 있는 이용권 입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 2 = 스트리밍 클럽
    {
        title: "스트리밍 클럽이란?",
        text: "기기 제한 없이 무제한 듣기 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },

    // 3 = 모바일 스트리밍 클럽
    {
        title: "모바일 스트리밍 클럽이란?",
        text: "모바일 기기에서 무제한 듣기 서비스가 제공되는 이용권입니다. (PC 미지원)",
        label: ['무제한 듣기'],
        data: [
            [false],
            [true],
            [true],
            [true],
            [false],
            [false],
            [true], //MELONUIT-477
        ]
    },
    // 4 = mp3 30 플러스
    {
        title: "MP3 30 플러스란?",
        text: "무제한 듣기 서비스와 MP3 30곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기', 'MP3 다운로드'],
        data: [
            [true, true],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 5 = mp3 50 플러스
    {
        title: "MP3 50 플러스란?",
        text: "무제한 듣기 서비스와 MP3 50곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기', 'MP3 다운로드'],
        data: [
            [true, true],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 6 = mp3 100 플러스
    {
        title: "MP3 100 플러스란?",
        text: "무제한 듣기 서비스와 MP3 100곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기', 'MP3 다운로드'],
        data: [
            [true, true],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 7 = mp3 30
    {
        title: "MP3 30이란?",
        text: "MP3 30곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['MP3 다운로드'],
        data: [
            [true],
            [true],
            [true],
            [false],
            [false],
            [false],
            [false],
        ]
    },
    // 8 = mp3 50
    {
        title: "MP3 50이란?",
        text: "MP3 50곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['MP3 다운로드'],
        data: [
            [true],
            [true],
            [true],
            [false],
            [false],
            [false],
            [false],
        ]
    },
    // 9 = mp3 100
    {
        title: "MP3 100이란?",
        text: "MP3 100곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['MP3 다운로드'],
        data: [
            [true],
            [true],
            [true],
            [false],
            [false],
            [false],
            [false],
        ]
    },
    // 10 = 프리클럽
    {
        title: "프리클럽이란?",
        text: "무제한 듣기 서비스와 DCF 다운로드 서비스(PC : 100곡, 모바일 : 무제한)가 제공되는 이용권입니다. DCF 파일이란 암호화가 적용된 파일로, 이용권 사용기간 동안 재생기간을 연장할 수 있습니다. (매월 연장 필요)",
        label: ['무제한 듣기', 'DCF 다운로드'],
        data: [
            [true, true],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 11 = 100회듣기
    {
        title: "100회 듣기란?",
        text: "실시간으로 100회 듣기가 가능한 이용권입니다.",
        label: ['횟수 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 12 = 300회듣기
    {
        title: "300회 듣기란?",
        text: "실시간으로 300회 듣기가 가능한 이용권입니다. ",
        label: ['횟수 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 13 = 어학 프리클럽
    {
        title: "어학 프리클럽이란?",
        text: "어학 컨텐츠에 한하여 기기 제한 없이 무제한 듣기 서비스와 DCF 무제한 다운로드 서비스가 제공되는 이용권입니다. DCF 파일이란 암호화가 적용된 파일로, 이용권 사용기간 동안 재생기간을 연장할 수 있습니다. (매월 연장 필요)",
        label: ['무제한 듣기', 'DCF 다운로드'],
        data: [
            [true, true],
            [true, true],
            [true, true],
            [true, false],
            [false, false],
            [true, false],
            [true, false],
        ]
    },
    // 14 = 어학 스트리밍클럽
    {
        title: "어학 스트리밍클럽이란?",
        text: "어학 컨텐츠에 한하여 기기 제한 없이 무제한 듣기 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [false],
            [true],
            [true],
        ]
    },
    // 15 = mp3 10 플러스
    {
        title: "MP3 10 플러스란?",
        text: "무제한 듣기 서비스와 MP3 10곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기', 'MP3 다운로드'],
        data: [
            [true, true],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 16 = mp3 10
    {
        title: "MP3 10이란?",
        text: "MP3 10곡 다운로드 서비스가 제공되는 이용권입니다.",
        label: ['MP3 다운로드'],
        data: [
            [true],
            [true],
            [true],
            [false],
            [false],
            [false],
            [false],
        ]
    },
    // 17 = 500회듣기
    {
        title: "500회 듣기란?",
        text: "실시간으로 500회 듣기가 가능한 이용권입니다. ",
        label: ['횟수 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 18 = 스트리밍 티켓
    {
        title: "스트리밍 티켓이란?",
        text: "기기 제한 없이 무제한 듣기 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 19 = 프리티켓
    {
        title: "프리티켓이란?",
        text: "무제한 듣기 서비스와 DCF 다운로드 서비스(PC : 100곡, 모바일 : 무제한)가 제공되는 이용권입니다. DCF 파일이란 암호화가 적용된 파일로, 이용권 사용기간 동안 재생기간을 연장할 수 있습니다. (매월 연장 필요)",
        label: ['무제한 듣기', 'DCF 다운로드'],
        data: [
            [true, true],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 20 = 어학 스트리밍티켓
    {
        title: "어학 스트리밍 티켓이란?",
        text: "어학 컨텐츠에 한하여 기기 제한 없이 무제한 듣기 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [false],
            [true],
            [true],
        ]
    },
    // 21 = HiFi 스트리밍티켓
    {
        title: "Hi-Fi 스트리밍 티켓이란?",
        text: "무손실 고음질 음원파일(FLAC)을 무제한으로 들을 수 있는 이용권 입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 22 = 모바일 스트리밍티켓
    {
        title: "모바일 스트리밍 티켓이란?",
        text: "모바일 기기에서 무제한 듣기 서비스가 제공되는 이용권입니다. (PC 미지원)",
        label: ['무제한 듣기'],
        data: [
            [false],
            [true],
            [true],
            [true],
            [false],
            [false],
            [true], //MELONUIT-477
        ]
    },
    // 23 = 어학 프리티켓
    {
        title: "어학 프리티켓이란?",
        text: "어학 컨텐츠에 한하여 기기 제한 없이 무제한 듣기 서비스가 제공되는 이용권입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [false],
            [true],
            [true],
        ]
    },
    // 24 = 스트리밍 플러스 티켓
    {
        title: "스트리밍 플러스 티켓이란?",
        text: "온라인과 오프라인에서 무제한 듣기가 가능한 이용권입니다. 오프라인 파일의 저장 및 재생은 인증된 모바일 디바이스 1대에서 가능하며, 오프라인 재생 기능을 통해 데이터 연결 없이 음악을 감상할 수 있습니다.",
        label: ['무제한 듣기', '오프라인 재생'],
        data: [
            [true, false],
            [true, true],
            [true, true],
            [true, false],
            [true, false],
            [true, false],
            [true, false],
        ]
    },
    // 25 = 어학 프리클럽 정기결제
    {
        title: "어학 전용 이용권이란?",
        text: "매일 업데이트 되는 EBS의 어학전문 컨텐츠를 무제한으로 들을 수 있는 이용권 입니다.",
        label: ['무제한 듣기'],
        data: [
            [true],
            [true],
            [true],
            [false],
            [false],
            [false],
            [false],
        ]
    },
    // 26 = 500 자동충전 티켓
    {
        title: "500회 듣기란?",
        text: "실시간으로 500회 듣기가 가능한 이용권입니다. \n 자동충전 이용권은 남은 듣기 횟수가 5곡 이하가 되면 자동으로 동일한 이용권이 결제되어 별도의 구매 없이 연속 이용이 가능합니다.",
        label: ['횟수 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 27 = 300 자동충전 티켓
    {
        title: "300회 듣기란?",
        text: "실시간으로 300회 듣기가 가능한 이용권입니다. \n 자동충전 이용권은 남은 듣기 횟수가 5곡 이하가 되면 자동으로 동일한 이용권이 결제되어 별도의 구매 없이 연속 이용이 가능합니다.",
        label: ['횟수 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 28 = 100 자동충전 티켓
    {
        title: "100회 듣기란?",
        text: "실시간으로 100회 듣기가 가능한 이용권입니다. \n 자동충전 이용권은 남은 듣기 횟수가 5곡 이하가 되면 자동으로 동일한 이용권이 결제되어 별도의 구매 없이 연속 이용이 가능합니다.",
        label: ['횟수 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
    // 29 = 30 자동충전 티켓
    {
        title: "30회 듣기란?",
        text: "실시간으로 30회 듣기가 가능한 이용권입니다. \n 자동충전 이용권은 남은 듣기 횟수가 5곡 이하가 되면 자동으로 동일한 이용권이 결제되어 별도의 구매 없이 연속 이용이 가능합니다.",
        label: ['횟수 듣기'],
        data: [
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
            [true],
        ]
    },
];