from opendbc.car import structs, get_safety_config
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.changan.values import CAR, CarControllerParams, ChanganSafetyFlags, CanBus, MIN_ACC_SPEED
from opendbc.car.changan.carstate import CarState
from opendbc.car.changan.carcontroller import CarController
from opendbc.car.changan.radar_interface import RadarInterface
from opendbc.car.carlog import carlog


SteerControlType = structs.CarParams.SteerControlType
GearShifter = structs.CarState.GearShifter
NetworkLocation = structs.CarParams.NetworkLocation
SafetyModel = structs.CarParams.SafetyModel


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController
  RadarInterface = RadarInterface

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    return CarControllerParams(CP).ACCEL_MIN, CarControllerParams(CP).ACCEL_MAX

  @staticmethod
  def init(CP, CP_SP, can_recv, can_send):
    # 香橙派(RK3588)移植运行在 PC 平台，openpilot 的自动关机逻辑
    # (system/hardware/hardwared.py -> power_monitoring.should_shutdown) 会在
    # panda 数据超时(DISCONNECT_TIMEOUT)时把 ignition 误判为熄火，进而置
    # DoShutdown 触发关机，导致行驶中设备随机重启。此处显式禁用。
    try:
      from openpilot.common.params import Params
    except ImportError:
      return

    try:
      params = Params()
      if not params.get_bool("DisablePowerDown"):
        params.put_bool("DisablePowerDown", True)
    except Exception:
      carlog.warning("failed to set DisablePowerDown")

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate: CAR, fingerprint, car_fw, experimental_long: bool, docs: bool) -> structs.CarParams:

    ret.brand = "changan"
    ret.safetyConfigs = [get_safety_config(SafetyModel.changan)]

    if candidate == CAR.CHANGAN_Z6:
      ret.safetyConfigs[0].safetyParam = int(ChanganSafetyFlags.CHANGAN_Z6_FLAG)
    elif candidate == CAR.CHANGAN_Z6_IDD:
      ret.safetyConfigs[0].safetyParam = int(ChanganSafetyFlags.CHANGAN_Z6_IDD_FLAG)
    elif candidate == CAR.CHANGAN_UNI_T:
      ret.safetyConfigs[0].safetyParam = int(ChanganSafetyFlags.CHANGAN_UNI_T_FLAG)

    ret.steerControlType = SteerControlType.angle

    ret.steerRatioRear = 0.0

    ret.steerActuatorDelay = 0.25
    ret.steerLimitTimer = 0.4

    ret.longitudinalTuning.kpBP = [0.0]
    ret.longitudinalTuning.kpV = [0.1]
    ret.longitudinalTuning.kiBP = [0.0]
    ret.longitudinalTuning.kiV = [0.0]

    ret.longitudinalActuatorDelay = 0.5
    ret.startAccel = 0.5
    ret.stopAccel = -2.0
    ret.stoppingDecelRate = 0.3
    ret.vEgoStarting = 0.5

    ret.openpilotLongitudinalControl = True
    ret.pcmCruise = False
    ret.minEnableSpeed = MIN_ACC_SPEED
    ret.minSteerSpeed = 0.0

    ret.radarUnavailable = True
    ret.networkLocation = NetworkLocation.gateway

    ret.autoResumeSng = True
    ret.enableBsm = False

    return ret
