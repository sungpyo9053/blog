// rclcpp node "pcb" with parameters gain (default 1.0) and mode (default "idle").
// argv[1] = case. Every callback call is logged with the parameters it received.
#include <chrono>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include <rclcpp/rclcpp.hpp>
#include <rclcpp/version.h>
#include <rcl_interfaces/msg/set_parameters_result.hpp>

using rcl_interfaces::msg::SetParametersResult;
using namespace std::chrono_literals;

static std::string fmt(const std::vector<rclcpp::Parameter> & ps)
{
  std::string s;
  for (auto & p : ps) {s += p.get_name() + "=" + p.value_to_string() + " ";}
  return s;
}

class Pcb : public rclcpp::Node
{
public:
  explicit Pcb(const std::string & c)
  : Node("pcb"), c_(c)
  {
    if (c_ != "after") {register_cbs();}
    declare_parameter("gain", 1.0);
    declare_parameter("mode", std::string("idle"));
    if (c_ == "after") {register_cbs();}
    if (c_ == "deferred") {
      timer_ = create_wall_timer(100ms, [this]() {
        if (!pending_) {return;}
        pending_ = false;
        auto r = set_parameter(rclcpp::Parameter("mode", "changed_by_timer"));
        RCLCPP_INFO(get_logger(), "timer set mode=changed_by_timer successful=%d", r.successful);
      });
    }
    RCLCPP_INFO(get_logger(), "READY gain=%s mode=%s on_set_calls=%d",
      get_parameter("gain").value_to_string().c_str(),
      get_parameter("mode").value_to_string().c_str(), calls_);
  }
  int calls_ = 0;
  std::string c_;

private:
  SetParametersResult on_set(const std::vector<rclcpp::Parameter> & ps)
  {
    ++calls_;
    RCLCPP_INFO(get_logger(), "CB#%d on_set got: %s", calls_, fmt(ps).c_str());
    SetParametersResult r;
    r.successful = true;
    for (auto & p : ps) {
      if (p.get_name() != "gain") {continue;}
      double v = p.as_double();
      if ((c_ == "reject" || c_ == "reject_init") && v > 2.5) {
        r.successful = false;
        r.reason = "gain must be <= 2.5";
      }
      if (c_ == "set_inside" && v == 3.0) {
        RCLCPP_INFO(get_logger(), "calling set_parameter(mode) inside on_set");
        auto ir = set_parameter(rclcpp::Parameter("mode", "changed"));
        RCLCPP_INFO(get_logger(), "inner set_parameter returned successful=%d", ir.successful);
      }
      if (c_ == "declare_inside" && v == 3.0) {
        RCLCPP_INFO(get_logger(), "calling declare_parameter(extra) inside on_set");
        declare_parameter("extra", 0);
        RCLCPP_INFO(get_logger(), "declare_parameter(extra) returned");
      }
      if (c_ == "deferred" && v == 3.0) {pending_ = true;}
    }
    return r;
  }

  void register_cbs()
  {
    auto cb = [this](const std::vector<rclcpp::Parameter> & ps) {return on_set(ps);};
    if (c_ == "discard") {
      add_on_set_parameters_callback(cb);  // returned handle dropped on purpose
      RCLCPP_INFO(get_logger(), "registered on_set, handle NOT stored");
      return;
    }
    h1_ = add_on_set_parameters_callback(cb);
    if (c_ == "two_cbs") {
      h2_ = add_on_set_parameters_callback([this](const std::vector<rclcpp::Parameter> & ps) {
        RCLCPP_INFO(get_logger(), "CB_B on_set got: %s", fmt(ps).c_str());
        SetParametersResult r;
        r.successful = true;
        return r;
      });
    }
    if (c_ == "pre_set" || c_ == "post_set" || c_ == "post_set_modify") {
#if RCLCPP_VERSION_MAJOR >= 21
      if (c_ == "pre_set") {
        pre_h_ = add_pre_set_parameters_callback([this](std::vector<rclcpp::Parameter> & ps) {
          RCLCPP_INFO(get_logger(), "PRE got: %s", fmt(ps).c_str());
          bool g3 = false;
          for (auto & p : ps) {if (p.get_name() == "gain" && p.as_double() == 3.0) {g3 = true;}}
          if (g3) {ps.emplace_back("mode", "auto_from_pre_set");}
        });
      }
      post_h_ = add_post_set_parameters_callback([this](const std::vector<rclcpp::Parameter> & ps) {
        RCLCPP_INFO(get_logger(), "POST got: %s", fmt(ps).c_str());
        if (c_ != "post_set_modify") {return;}
        for (auto & p : ps) {
          if (p.get_name() == "gain" && p.as_double() == 3.0) {
            RCLCPP_INFO(get_logger(), "calling set_parameter(mode) inside post_set");
            auto ir = set_parameter(rclcpp::Parameter("mode", "changed_in_post"));
            RCLCPP_INFO(get_logger(), "inner set_parameter returned successful=%d", ir.successful);
          }
        }
      });
#else
      RCLCPP_INFO(get_logger(), "NOT AVAILABLE: rclcpp %d has no add_pre/post_set_parameters_callback",
        RCLCPP_VERSION_MAJOR);
#endif
    }
  }

  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr h1_, h2_;
#if RCLCPP_VERSION_MAJOR >= 21
  rclcpp::node_interfaces::PreSetParametersCallbackHandle::SharedPtr pre_h_;
  rclcpp::node_interfaces::PostSetParametersCallbackHandle::SharedPtr post_h_;
#endif
  bool pending_ = false;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  std::string c = argc > 1 ? argv[1] : "before";
  auto n = std::make_shared<Pcb>(c);
  if (c == "no_spin") {
    while (rclcpp::ok()) {std::this_thread::sleep_for(100ms);}
  } else {
    rclcpp::spin(n);
  }
  std::printf("EXIT gain=%s mode=%s on_set_calls=%d\n",
    n->get_parameter("gain").value_to_string().c_str(),
    n->get_parameter("mode").value_to_string().c_str(), n->calls_);
  rclcpp::shutdown();
  return 0;
}
