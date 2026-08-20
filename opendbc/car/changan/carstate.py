import copy
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.common.filter_simple import FirstOrderFilter
from opendbc.car import Bus, structs, DT_CTRL
from opendbc.can.can_define import CANDefine
from opendbc.can.parser import CANParser
from opendbc.car.interfaces import CarStateBase
from opendbc.car.changan.values import CAR, DBC, STEER_THRESHOLD, EPS_SCALE


TEMP_STEER_FAULTS = (0, 9, 11, 21, 25)
PERM_STEER_FAULTS = (3, 17)


class CarState(CarStateBase):
  def __init__(self, CP):
    super().__init__(CP)
    can_define = CANDefine(DBC[CP.carFingerprint][Bus.pt])

    if self.CP.carFingerprint == CAR.CHANGAN_Z6:
      self.shifter_values = can_define.dv["GW_338"]["TCU_GearForDisplay"]
    elif self.CP.carFingerprint == CAR.CHANGAN_Z6_IDD:
      self.shifter_values = can_define.dv["GW_338"]["TCU_GearForDisplay"]
    elif self.CP.carFingerprint == CAR.CHANGAN_UNI_T:
      self.shifter_values = None  # UNI-T gear is decoded from GW_1A8.GearPosition in update()
      self.gear_names = {0: "P", 1: "N", 9: "R", 10: "D"}
    self.eps_torque_scale = EPS_SCALE[CP.carFingerprint] / 100.0
    self.cluster_speed_hyst_gap = CV.KPH_TO_MS / 2.0
    self.cluster_min_speed = CV.KPH_TO_MS / 2.0

    self.angle_offset = FirstOrderFilter(None, 60.0, DT_CTRL, initialized=False)

    self.prev_distance_button = 0
    self.distance_button = 0
    self.pcm_follow_distance = 0
    self.low_speed_lockout = False
    self.acc_type = 1
    self.cruiseEnable = False
    self.cruiseEnablePrev = False
    self.cruiseSpeed = 0
    self.buttonPlus = 0
    self.buttonReduce = 0

    self.counter_244 = 0
    self.counter_1ba = 0
    self.counter_17e = 0
    self.counter_307 = 0
    self.counter_31a = 0

    self.sigs244 = {}
    self.sigs1ba = {}
    self.sigs17e = {}
    self.sigs307 = {}
    self.sigs31a = {}

    self.steeringPressed = False
    self.steeringPressedMax = 0
    self.steeringPressedMin = 0

    self.iacc_enable_switch_button_pressed = 0
    self.iacc_enable_switch_button_prev = 0
    self.iacc_enable_switch_button_rising_edge = False

    self.cruise_control_mode = 0  # default mode; cruise speed resets to current on engage

  def update(self, can_parsers) -> structs.CarState:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]
    ret = structs.CarState()

    if self.CP.carFingerprint == CAR.CHANGAN_UNI_T:
      ret.doorOpen = False
      ret.seatbeltUnlatched = False
    else:
      ret.doorOpen = any([cp.vl["GW_28B"]["BCM_DriverDoorStatus"]])
      ret.seatbeltUnlatched = cp.vl["GW_50"]["SRS_DriverBuckleSwitchStatus"] == 1
    ret.parkingBrake = False

    if self.CP.carFingerprint == CAR.CHANGAN_Z6_IDD:
      carspd = cp.vl["GW_17A"]["ESP_VehicleSpeed"]
    else:
      carspd = cp.vl["GW_187"]["ESP_VehicleSpeed"]

    speed = carspd if carspd <= 5 else ((carspd / 0.98) + 2)
    ret.vEgoRaw = speed * CV.KPH_TO_MS
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)
    ret.vEgoCluster = ret.vEgo

    ret.standstill = abs(ret.vEgoRaw) < 1e-3

    ret.steeringAngleOffsetDeg = 0
    ret.steeringAngleDeg = cp.vl["GW_180"]["SAS_SteeringAngle"]
    ret.steeringRateDeg = cp.vl["GW_180"]["SAS_SteeringAngleSpeed"]

    if self.CP.carFingerprint == CAR.CHANGAN_Z6_IDD:
      can_gear = int(cp.vl["GW_338"]["TCU_GearForDisplay"])
      ret.brakePressed = cp.vl["GW_1A6"]["EMS_BrakePedalStatus"] != 0
      ret.gasPressed = cp.vl["GW_1C6"]["EMS_RealAccPedal"] != 0
      self.steeringPressedMin = 1
      self.steeringPressedMax = 3
      ret.leftBlindspot = False
      ret.rightBlindspot = False
    elif self.CP.carFingerprint == CAR.CHANGAN_UNI_T:
      gear_raw = int(cp.vl["GW_1A8"]["GearPosition"])  # 0=P 1=N 9=R 10=D
      ret.brakePressed = cp.vl["GW_277"]["ESP_BrakePedalStatus"] != 0   # byte0 bit7
      ret.gasPressed = cp.vl["GW_26A"]["EMS_AccelSwitch"] != 0    # byte0 bit0
      self.steeringPressedMin = 1
      self.steeringPressedMax = 6
      ret.leftBlindspot = False
      ret.rightBlindspot = False
    else:
      can_gear = int(cp.vl["GW_338"]["TCU_GearForDisplay"])
      ret.brakePressed = cp.vl["GW_196"]["EMS_BrakePedalStatus"] != 0
      ret.gasPressed = cp.vl["GW_196"]["EMS_RealAccPedal"] != 0
      self.steeringPressedMin = 1
      self.steeringPressedMax = 6
      ret.leftBlindspot = False
      ret.rightBlindspot = False

    if self.CP.carFingerprint == CAR.CHANGAN_UNI_T:
      ret.gearShifter = self.parse_gear_shifter(self.gear_names.get(gear_raw, None))
    else:
      ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(can_gear, None))

    ret.leftBlinker, ret.rightBlinker = self.update_blinker_from_stalk(
      200, cp.vl["GW_28B"]["BCM_TurnIndicatorLeft"] == 1, cp.vl["GW_28B"]["BCM_TurnIndicatorRight"] == 1
    )

    ret.steeringTorque = cp.vl["GW_17E"]["EPS_MeasuredTorsionBarTorque"]
    ret.steeringTorqueEps = cp.vl["GW_170"]["EPS_ActualTorsionBarTorq"]

    if self.steeringPressed:
      if abs(ret.steeringTorque) < self.steeringPressedMin and abs(ret.steeringAngleDeg) < 90:
        self.steeringPressed = False
    else:
      if abs(ret.steeringTorque) > self.steeringPressedMax:
        self.steeringPressed = True
    ret.steeringPressed = self.steeringPressed

    ret.steerFaultTemporary = cp.vl["GW_24F"]["EPS_EPSFailed"] != 0 or cp.vl["GW_17E"]["EPS_LatCtrlAvailabilityStatus"] == 2

    # GW_28C signal names differ per PT DBC: UNI-T uses changan_unit_pt.dbc
    # (CruiseButton/CruiseCancel/CruiseResume/CruiseSet/IaccButton), while
    # Z6 / Z6 iDD use changan_pt.dbc (GW_MFS_* names).
    if self.CP.carFingerprint == CAR.CHANGAN_UNI_T:
      gw28c = cp.vl["GW_28C"]
      iacc_btn = gw28c["IaccButton"]
      res_btn = gw28c["CruiseResume"]
      set_btn = gw28c["CruiseSet"]
    else:
      gw28c = cp.vl["GW_28C"]
      iacc_btn = gw28c["GW_MFS_IACCenable_switch_signal"]
      res_btn = gw28c["GW_MFS_RESPlus_switch_signal"]
      set_btn = gw28c["GW_MFS_SETReduce_switch_signal"]

    self.iacc_enable_switch_button_pressed = iacc_btn
    self.iacc_enable_switch_button_rising_edge = self.iacc_enable_switch_button_pressed == 1 and self.iacc_enable_switch_button_prev == 0

    if self.cruiseEnable and (self.iacc_enable_switch_button_rising_edge or ret.brakePressed):
      self.cruiseEnable = False
    elif not self.cruiseEnable and self.iacc_enable_switch_button_rising_edge:
      self.cruiseEnable = True

    self.iacc_enable_switch_button_prev = self.iacc_enable_switch_button_pressed

    if self.cruiseEnable and not self.cruiseEnablePrev:
      self.cruiseSpeed = speed if self.cruiseSpeed == 0 or self.cruise_control_mode == 0 else self.cruiseSpeed

    if res_btn == 1 and self.buttonPlus == 0 and self.cruiseEnable:
      self.cruiseSpeed = ((self.cruiseSpeed // 5) + 1) * 5

    if set_btn == 1 and self.buttonReduce == 0 and self.cruiseEnable:
      self.cruiseSpeed = max((((self.cruiseSpeed // 5) - 1) * 5), 0)

    self.cruiseEnablePrev = self.cruiseEnable
    self.buttonPlus = res_btn
    self.buttonReduce = set_btn

    # NOTE: the UNI-T 2022 captures (01/02/dangwei.csv) show the ADAS
    # command messages (0x1BA/0x244/0x307/0x31A) only on bus 0 (100Hz, relayed
    # by the gateway) - bus 2 (cam) is silent except the first 0.1s of the
    # capture.  Z6 / Z6 iDD keep reading them from bus 2 (cam).
    if self.CP.carFingerprint == CAR.CHANGAN_UNI_T:
      adas_src = cp
    else:
      adas_src = cp_cam
    ret.accFaulted = adas_src.vl["GW_244"]["ACC_ACCMode"] == 7 or adas_src.vl["GW_31A"]["ACC_IACCHWAMode"] == 7
    ret.cruiseState.available = adas_src.vl["GW_31A"]["ACC_IACCHWAEnable"] == 1
    ret.cruiseState.speed = self.cruiseSpeed * CV.KPH_TO_MS
    cluster_set_speed = self.cruiseSpeed

    if ret.cruiseState.speed != 0:
      ret.cruiseState.speedCluster = cluster_set_speed * CV.KPH_TO_MS

    ret.stockFcw = adas_src.vl["GW_244"]["ACC_FCWPreWarning"] == 1
    ret.cruiseState.standstill = ret.standstill
    ret.cruiseState.enabled = self.cruiseEnable
    ret.genericToggle = False
    ret.stockAeb = adas_src.vl["GW_244"]["ACC_AEBCtrlType"] > 0

    self.sigs244 = copy.copy(adas_src.vl["GW_244"])
    self.sigs1ba = copy.copy(adas_src.vl["GW_1BA"])
    self.sigs17e = copy.copy(cp.vl["GW_17E"])
    self.sigs307 = copy.copy(adas_src.vl["GW_307"])
    self.sigs31a = copy.copy(adas_src.vl["GW_31A"])
    self.counter_244 = adas_src.vl["GW_244"]["ACC_RollingCounter_24E"]
    self.counter_1ba = adas_src.vl["GW_1BA"]["ACC_RollingCounter_1BA"]
    self.counter_17e = cp.vl["GW_17E"]["EPS_RollingCounter_17E"]
    self.counter_307 = adas_src.vl["GW_307"]["ACC_RollingCounter_35E"]
    self.counter_31a = adas_src.vl["GW_31A"]["ACC_RollingCounter_36D"]

    self.prev_distance_button = self.distance_button
    self.distance_button = adas_src.vl["GW_307"]["ACC_DistanceLevel"]

    return ret

  @staticmethod
  def get_can_parsers(CP):
    pt_messages = [
      ("GW_28B", 0),
      ("GW_187", 0),
      ("GW_17E", 0),
      ("GW_170", 0),
      ("GW_180", 0),
      ("GW_24F", 0),
      ("GW_28C", 0),
      ("GW_1BA", 0),
      ("GW_244", 0),
      ("GW_307", 0),
      ("GW_31A", 0),
    ]
    if CP.carFingerprint == CAR.CHANGAN_UNI_T:
      pt_messages += [("GW_1A8", 0), ("GW_277", 0), ("GW_26A", 0)]
    else:
      pt_messages += [("GW_338", 0), ("GW_17A", 0), ("GW_1C6", 0), ("GW_50", 0), ("GW_196", 0), ("GW_1A6", 0)]
    cam_messages = [
      ("GW_244", 0),
      ("GW_1BA", 0),
      ("GW_307", 0),
      ("GW_31A", 0),
    ]
    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], pt_messages, 0),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], cam_messages, 2),
    }
