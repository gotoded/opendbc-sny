from opendbc.car.changan.can_crc import CanCrc

can_crc = CanCrc()


def create_244_command_a05(packer, accel, counter, longActive, accTrq):
  values = {
    "ACC_ACCTargetAcceleration": accel,
    "ACC_AEBTargetDeceleration": -0.0005,
    "unknown": 1,
    "ACC_CDDActive": 1 if accel < 0 else 0,
    "ACC_LDWStatus": 0,
    "ACC_LDWVibrationWarningReq": 0,
    "ACC_LKAStatus": 0,
    "ACC_TextInfoForDriver": 0,
    "ACC_RollingCounter_24E": counter,
    "ACC_CRCCheck_24E": 0,
    "ACC_RollingCounter_25E": counter,
    "ACC_CRCCheck_25E": 0,
    "ADS_RollingCounter_244": counter,
    "ADS_CRCCheck_244": 0,
    "ACC_ACCMode": 3 if longActive else 2,
    "ACC_AEBActive": 0,
    "ACC_AccTrqReq": (120 + (accel - 0.05) / 0.05 * 30) if accel > 0 else 5005,
    "ACC_AccTrqReqActive": 1 if longActive and accel > 0 else 0,
    "ACC_FCWPreWarning": 0,
    "ACC_FCWLatentWarning": 0,
    "ACC_AWBActive": 0,
    "ACC_AEBCtrlType": 0,
    "ACC_LatTakeoverReq": 0,
    "ACC_LngTakeOverReq": 0,
    "ADS_EOMTOReq": 0,
    "ACC_HandsOnReq": 0,
  }
  dat = packer.make_can_msg("GW_244", 0, values)[1]
  values["ACC_CRCCheck_24E"] = can_crc.crc_calculate_crc8(dat[:7])
  values["ACC_CRCCheck_25E"] = can_crc.crc_calculate_crc8(dat[8:15])
  dat = packer.make_can_msg("GW_244", 0, values)[1]
  values["ADS_CRCCheck_244"] = can_crc.crc16_ccitt_false(dat[:54])
  return packer.make_can_msg("GW_244", 0, values)


def create_244_command(packer, msg: dict, accel, counter, longActive, accTrq, vEgoRaw, is_unit: bool):
  values = msg.copy()
  if is_unit:
    # UNIT 2022 DBC (changan_unit_pt.dbc): ACC_ACCMode=54|3@0+,
    # ACC_AccTrqReq=103|16@0+ (Motorola, unsigned).  Keep camera-relayed
    # ACC_ACCMode; only update accel/counter/torque.
    values.update(
      {
        "ACC_ACCTargetAcceleration": accel,
        "ACC_RollingCounter_24E": counter,
        "ACC_RollingCounter_25E": counter,
        "ACC_AccTrqReq": accTrq,
        "ACC_AccTrqReqActive": 1 if longActive and accel >= 0 else 0,
      }
    )
  else:
    # Z6 / Z6 iDD original behavior
    values.update(
      {
        "ACC_ACCTargetAcceleration": accel,
        "ACC_CDDActive": 1 if longActive and accel < 0 else 0,
        "ACC_RollingCounter_24E": counter,
        "ACC_RollingCounter_25E": counter,
        "ACC_ACCMode": 3 if longActive else 2,
        "ACC_AccTrqReq": accTrq,
        "ACC_AccTrqReqActive": 1 if longActive and accel >= 0 else 0,
      }
    )
  dat = packer.make_can_msg("GW_244", 0, values)[1]
  values["ACC_CRCCheck_24E"] = can_crc.crc_calculate_crc8(dat[:7])
  values["ACC_CRCCheck_25E"] = can_crc.crc_calculate_crc8(dat[8:15])
  return packer.make_can_msg("GW_244", 0, values)


def create_244_command_idd(packer, msg: dict, accel, counter, longActive, accTrq, vEgoRaw):
  values = msg.copy()
  values.update(
    {
      "ACC_ACCTargetAcceleration": accel,
      "ACC_CDDActive": 1 if longActive and accel < 0 else 0,
      "ACC_RollingCounter_24E": counter,
      "ACC_RollingCounter_25E": counter,
      "ACC_ACCMode": 3 if longActive else 2,
      "ACC_AccTrqReq": accTrq,
      "ACC_AccTrqReqActive": 1 if longActive and accel >= 0 else 0,
      "ACC_DecToStop": 1 if longActive and accel < 0 and vEgoRaw == 0 else 0,
      "ACC_AWBActive": 0,
      "ACC_AEBCtrlType": 0,
      "ACC_TextInfoForDriver": 0,
      "ACC_Driveoff_Request": 0,
      "ACC_FCWPreWarning": 0,
      "ACC_FCWLatentWarning": 0,
      "ACC_LatTakeoverReq": 0,
      "ACC_LngTakeOverReq": 0,
      "ACC_HandsOnReq": 0,
    }
  )
  dat = packer.make_can_msg("GW_244", 0, values)[1]
  values["ACC_CRCCheck_24E"] = can_crc.crc_calculate_crc8(dat[:7])
  values["ACC_CRCCheck_25E"] = can_crc.crc_calculate_crc8(dat[8:15])
  return packer.make_can_msg("GW_244", 0, values)


def create_1BA_command(packer, msg: dict, angle, latCtrlActive, counter):
  # Both changan_unit_pt.dbc (UNI-T 2022) and changan_pt.dbc (Z6 / Z6 iDD)
  # define EPS_AngleCmd as a 16-bit Motorola signal with scale 0.1 deg, so the
  # same encoding works for all platforms: relay the camera frame verbatim and
  # only update the angle command, lateral-control flag, rolling counter, then
  # recompute the CRC-8 (init=0x6C) over bytes 0..6.
  values = msg.copy()
  values.update(
    {
      "EPS_AngleCmd": angle,
      "EPS_LatCtrlActive": latCtrlActive,
      "ACC_RollingCounter_1BA": counter,
    }
  )
  dat = packer.make_can_msg("GW_1BA", 0, values)[1]

  values["ACC_CRCCheck_1BA"] = can_crc.crc_calculate_crc8(dat[:7])
  return packer.make_can_msg("GW_1BA", 0, values)


def create_17E_command(packer, msg: dict, longActive, counter):
  # Relay EPS sensor frame (bus 2); bump counter, recompute CRC.
  # msg comes from CS.sigs17e (DBC-defined signals only).
  values = msg.copy()
  values.update(
    {
      "EPS_MeasuredTorsionBarTorque": msg.get("EPS_MeasuredTorsionBarTorque", 0) + 1 if longActive else msg.get("EPS_MeasuredTorsionBarTorque", 0),
      "EPS_RollingCounter_17E": counter,
    }
  )
  dat = packer.make_can_msg("GW_17E", 0, values)[1]
  values["EPS_CRCCheck_17E"] = can_crc.crc_calculate_crc8(dat[:7])

  return packer.make_can_msg("GW_17E", 2, values)


def create_307_command(packer, msg: dict, counter, cruiseSpeed):
  # Relay the camera's original GW_307 display frame; only bump the 4
  # rolling counters and the set speed.  msg comes from CS.sigs307
  # (CANParser dict of the DBC-defined signals), so a plain copy preserves
  # every byte of the original frame.
  values = msg.copy()
  values.update(
    {
      "ACC_SetSpeed": cruiseSpeed,
      "ACC_RollingCounter_35E": counter,
      "ACC_RollingCounter_322": counter,
      "ACC_RollingCounter_344": counter,
      "ACC_RollingCounter_35F": counter,
    }
  )
  dat = packer.make_can_msg("GW_307", 0, values)[1]
  values["ACC_CRCCheck_35E"] = can_crc.crc_calculate_crc8(dat[:7])
  values["ACC_CRCCheck_322"] = can_crc.crc_calculate_crc8(dat[8:15])
  values["ACC_CRCCheck_344"] = can_crc.crc_calculate_crc8(dat[16:23])
  values["ACC_CRCCheck_35F"] = can_crc.crc_calculate_crc8(dat[24:31])
  return packer.make_can_msg("GW_307", 0, values)


def create_31A_command(packer, msg: dict, counter, longActive, steeringPressed):
  # Relay the camera's original GW_31A frame; only bump the 4 rolling
  # counters.  msg comes from CS.sigs31a.
  values = msg.copy()
  values.update(
    {
      "ACC_RollingCounter_36D": counter,
      "ACC_RollingCounter_30A": counter,
      "ACC_RollingCounter_30D": counter,
      "ACC_RollingCounter_367": counter,
    }
  )
  dat = packer.make_can_msg("GW_31A", 0, values)[1]
  values["ACC_CRCCheck_36D"] = can_crc.crc_calculate_crc8(dat[:7])
  values["ACC_CRCCheck_30A"] = can_crc.crc_calculate_crc8(dat[8:15])
  values["ACC_CRCCheck_30D"] = can_crc.crc_calculate_crc8(dat[16:23])
  values["ACC_CRCCheck_367"] = can_crc.crc_calculate_crc8(dat[24:31])
  return packer.make_can_msg("GW_31A", 0, values)
