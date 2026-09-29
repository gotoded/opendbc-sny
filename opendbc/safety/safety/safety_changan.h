// Safety model for Changan Z6 / Z6 IDD
// Reversed from opendbc/car/changan/{carcontroller.py, changancan.py, values.py}
//
// Reverse engineering notes:
// - TX whitelist derived from changancan.py packer.make_can_msg() calls
// - RX whitelist derived from carstate.py cp.vl[] / cp_cam.vl[] lookups
// - Safety flags derived from values.py ChanganSafetyFlags enum
// - Bus topology: ESC=0 (pt), MRR=1, MPC/cam=2
//
// TX Messages (openpilot → car):
//   0x1BA (GW_1BA)  bus 0: EPS angle command (lateral)
//   0x17E (GW_17E)  bus 2: EPS torque sensor relay + lat active flag
//   0x244 (GW_244)  bus 0: ACC longitudinal command
//   0x307 (GW_307)  bus 0: ACC display / set speed relay
//   0x31A (GW_31A)  bus 0: IACC/HWA mode + AEB relay

#pragma once

#include "safety_declarations.h"

// ── Safety flags ──────────────────────────────────────────────────────────────
#define CHANGAN_Z6_FLAG     0x1U   // Standard Z6 (Veoneer MPC/radar solution)
#define CHANGAN_Z6_IDD_FLAG 0x4U   // Changan Z6 IDD variant
#define CHANGAN_UNI_T_FLAG  0x10U  // Changan UNI-T 2022

// ── Steering limits ───────────────────────────────────────────────────────────
// The two DBCs encode EPS_AngleCmd differently, so the units differ per platform:
//   Z6 / Z6 iDD (changan_pt.dbc)     : 0.1 deg/LSB    -> angle_cmd is in 0.1 deg
//   UNI-T 2022 (changan_unit_pt.dbc) : 1/1024 deg/LSB -> angle_cmd is in 1/64 deg
//     (changan_tx_hook divides the 24-bit field by 16, and 1024/16 = 64)
#define CHANGAN_UNIT_TICKS_PER_DEG 64

// Z6 / Z6 iDD: STEER_MAX from values.py = 980 deg (9800 raw), and the rate limit
// from ANGLE_LIMITS = 1.4 deg/frame (14 raw at 100Hz)
#define CHANGAN_STEER_ANGLE_MAX_Z6  9800    // 980 deg * 10
#define CHANGAN_STEER_ANGLE_RATE_Z6 14      // 1.4 deg * 10 = 14 per frame

// UNI-T 2022:
//   absolute limit = the vehicle's own SAS range, +/-512 deg (GW_180)
//   rate limit = 3 deg/frame (300 deg/s): ~2x headroom over openpilot's own
//     1.4 deg/frame ramp (values.py ANGLE_LIMITS) and ~4x over the fastest
//     manual steering seen in a 290 s capture (0.78 deg/frame)
#define CHANGAN_STEER_ANGLE_MAX_UNIT  (512 * CHANGAN_UNIT_TICKS_PER_DEG)  // 32768
#define CHANGAN_STEER_ANGLE_RATE_UNIT (3 * CHANGAN_UNIT_TICKS_PER_DEG)    // 192

// ── Acceleration limits ───────────────────────────────────────────────────────
// ACC_ACCTargetAcceleration: factor 0.05 m/s² per LSB
// ACCEL_MAX = 2.0 m/s²  → 40 raw
// ACCEL_MIN = -3.5 m/s² → -70 raw
#define CHANGAN_ACCEL_MAX   40    //  2.0 m/s² * 20
#define CHANGAN_ACCEL_MIN  -70    // -3.5 m/s² * 20
// UNI-T 2022 encodes ACC_ACCTargetAcceleration differently
// (changan_unit_pt.dbc: 7|16@0- (0.001,-25.6), 16-bit big-endian over bytes 0..1):
//   raw = (accel + 25.6) * 1000  ->  +2.0 m/s² = 27600, -3.5 m/s² = 22100
#define CHANGAN_UNIT_ACCEL_MAX 27600   //  2.0 m/s²
#define CHANGAN_UNIT_ACCEL_MIN 22100   // -3.5 m/s²

// ── RX messages ───────────────────────────────────────────────────────────────
// bus 0 (ESC/pt CAN)
#define MSG_GW_50    0x050U   // SRS seatbelt
#define MSG_GW_170   0x170U   // EPS actual torque
#define MSG_GW_17A   0x17AU   // ESP speed (Z6 IDD variant)
#define MSG_GW_17E   0x17EU   // EPS sensor (also TX relay on bus 2)
#define MSG_GW_180   0x180U   // SAS steering angle + rate
#define MSG_GW_187   0x187U   // ESP speed        (default Z6)
#define MSG_GW_196   0x196U   // EMS brake+accel  (default Z6)
#define MSG_GW_1A6   0x1A6U   // EMS brake (Z6 IDD)
#define MSG_GW_1C6   0x1C6U   // EMS accel (Z6 IDD)
#define MSG_GW_24F   0x24FU   // EPS fault status
#define MSG_GW_28B   0x28BU   // BCM doors + turn signals
#define MSG_GW_28C   0x28CU   // MFS steering wheel buttons
#define MSG_GW_39B   0x39BU   // TCU gear         (UNIT 2022)
#define MSG_GW_338   0x338U   // TCU gear          (default Z6 / IDD)

// bus 2 (MPC/cam CAN)
#define MSG_GW_1BA   0x1BAU   // ACC angle cmd (also TX on bus 0 via relay)
#define MSG_GW_244   0x244U   // ACC longitudinal  (also TX on bus 0 via relay)
#define MSG_GW_307   0x307U   // ACC display       (also TX relay)
#define MSG_GW_31A   0x31AU   // IACC/HWA          (also TX relay)

// ── TX messages ───────────────────────────────────────────────────────────────
#define MSG_GW_1BA_TX  0x1BAU  // bus 0: lateral angle command
#define MSG_GW_17E_TX  0x17EU  // bus 2: EPS torque relay
#define MSG_GW_244_TX  0x244U  // bus 0: longitudinal command
#define MSG_GW_307_TX  0x307U  // bus 0: set speed relay
#define MSG_GW_31A_TX  0x31AU  // bus 0: IACC mode relay

// ── State variables ───────────────────────────────────────────────────────────
static uint32_t changan_safety_flags = 0U;
static int changan_desired_angle_last = 0;

// ── TX messages ───────────────────────────────────────────────────────────────
static const CanMsg CHANGAN_TX_MSGS[] = {
  {MSG_GW_1BA_TX, 0, 32, false},  // EPS lateral angle command
  {MSG_GW_17E_TX, 2, 8,  true},   // EPS relay (bus 2 = cam)
  {MSG_GW_244_TX, 0, 32, false},  // ACC longitudinal
  {MSG_GW_307_TX, 0, 64, false},  // ACC display relay
  {MSG_GW_31A_TX, 0, 64, false},  // IACC mode relay
};

// ── RX allowed messages ───────────────────────────────────────────────────────
static RxCheck changan_rx_checks[] = {
  // bus 0 (pt)
  {.msg = {{MSG_GW_50,   0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 10U},
           {MSG_GW_50,   0, 4,  .ignore_checksum = true, .ignore_counter = true, .frequency = 10U},
           {0}}},
  {.msg = {{MSG_GW_170,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U}, {0}, {0}}},
  {.msg = {{MSG_GW_17E,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U}, {0}, {0}}},
  {.msg = {{MSG_GW_180,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U}, {0}, {0}}},
  {.msg = {{MSG_GW_24F,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 20U}, {0}, {0}}},
  {.msg = {{MSG_GW_28B,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 10U}, {0}, {0}}},
  {.msg = {{MSG_GW_28C,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 20U}, {0}, {0}}},
  {.msg = {{MSG_GW_187,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U},
           {MSG_GW_17A,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U},
           {0}}},
  {.msg = {{MSG_GW_196,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U},
           {MSG_GW_1A6,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U},
           {MSG_GW_1C6,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 100U}}},
  {.msg = {{MSG_GW_338,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 20U},
           {MSG_GW_39B,  0, 8,  .ignore_checksum = true, .ignore_counter = true, .frequency = 10U},
           {0}}},
  // These messages are relayed on bus 0 by the gateway (UNI-T 2022 captures
  // show them only on bus 0; bus 2/cam is silent)
  {.msg = {{MSG_GW_1BA,  0, 32, .ignore_checksum = true, .ignore_counter = true, .frequency = 100U}, {0}, {0}}},
  {.msg = {{MSG_GW_244,  0, 32, .ignore_checksum = true, .ignore_counter = true, .frequency = 50U}, {0}, {0}}},
  {.msg = {{MSG_GW_307,  0, 64, .ignore_checksum = true, .ignore_counter = true, .frequency = 10U}, {0}, {0}}},
  {.msg = {{MSG_GW_31A,  0, 64, .ignore_checksum = true, .ignore_counter = true, .frequency = 10U}, {0}, {0}}},
};

// ── Safety hook: init ─────────────────────────────────────────────────────────
static safety_config changan_init(uint16_t param) {
  changan_safety_flags = param;
  changan_desired_angle_last = 0;
  return BUILD_SAFETY_CFG(changan_rx_checks, CHANGAN_TX_MSGS);
}

// ── Safety hook: TX allowed ───────────────────────────────────────────────────
// Validates each outgoing message against:
//   1. Steering angle limits  (GW_1BA)
//   2. Acceleration limits    (GW_244)
// Note: TX whitelist is already checked by safety_tx_hook in safety.h
static bool changan_tx_hook(const CANPacket_t *to_send) {
  const int addr = GET_ADDR(to_send);
  const int bus  = GET_BUS(to_send);
  bool tx = true;

  // ── GW_1BA: lateral angle command ────────────────────────────────────────
  if ((addr == MSG_GW_1BA_TX) && (bus == 0)) {
    int angle_cmd, angle_max, angle_rate;
    if (changan_safety_flags & CHANGAN_UNI_T_FLAG) {
      // UNI-T 2022: EPS_AngleCmd spans bytes 2..4 as a 24-bit big-endian value
      //   raw24 = 0x5DC200 + angle_deg * 1024   (1/1024 deg/LSB)
      // Verified over a 290 s capture: raw24 - 0x5DC200 == GW_180
      // SAS_SteeringAngle raw * 16, i.e. the same physical angle as 0x180.
      //   -> angle_cmd = (raw24 - 0x5DC200) / 16 = angle_deg * 64
      const int raw24 = ((int)GET_BYTE(to_send, 2) << 16) | ((int)GET_BYTE(to_send, 3) << 8) | (int)GET_BYTE(to_send, 4);
      angle_cmd = (raw24 - 0x5DC200) / 16;
      angle_max = CHANGAN_STEER_ANGLE_MAX_UNIT;
      angle_rate = CHANGAN_STEER_ANGLE_RATE_UNIT;
    } else {
      // Z6 / Z6 iDD: EPS_AngleCmd bits [1..14], factor 0.1 deg/LSB, signed
      const int raw_angle = (int)(((GET_BYTE(to_send, 0) >> 1) | (GET_BYTE(to_send, 1) << 7)) & 0x3FFFU);
      angle_cmd = (raw_angle & 0x2000) ? (raw_angle - 0x4000) : raw_angle;
      angle_max = CHANGAN_STEER_ANGLE_MAX_Z6;
      angle_rate = CHANGAN_STEER_ANGLE_RATE_Z6;
    }

    // GW_1BA carries no usable "lateral control active" bit.  The
    // reverse-engineered EPS_LatCtrlActive (bit 16) is just the LSB of the
    // 24-bit angle field, and byte0 - which the old code latched as bit0 - is
    // ACC_MotorTorqueMinLimitRequest (0xB5 / 0x80), not a flag.  In a 290 s
    // capture byte5 is always 0, byte6 is the rolling counter, byte7 the CRC
    // and bytes 8..31 are always 0, so no bit ever toggles with engagement.
    // The rate limit is therefore applied unconditionally.
    const int angle_delta = angle_cmd - changan_desired_angle_last;

    if ((angle_delta > angle_rate) || (angle_delta < -angle_rate)) {
      tx = false;
    }
    if ((angle_cmd > angle_max) || (angle_cmd < -angle_max)) {
      tx = false;
    }

    // Slew `last` toward the command by at most angle_rate per frame.  Updating
    // it unconditionally stops the reference from freezing: the old code only
    // updated it when the frame was allowed, so one rejected frame (e.g. the
    // first frame after engaging at a large steering angle) blocked every later
    // frame permanently.
    if (angle_delta > angle_rate) {
      changan_desired_angle_last += angle_rate;
    } else if (angle_delta < -angle_rate) {
      changan_desired_angle_last -= angle_rate;
    } else {
      changan_desired_angle_last = angle_cmd;
    }
  }

  // ── GW_244: longitudinal acceleration command ─────────────────────────────
  if ((addr == MSG_GW_244_TX) && (bus == 0)) {
    if (changan_safety_flags & CHANGAN_UNI_T_FLAG) {
      // UNI-T 2022: ACC_ACCTargetAcceleration is a 16-bit big-endian field over
      // bytes 0..1 (changan_unit_pt.dbc: 7|16@0- (0.001,-25.6)).  Reading only
      // byte0 - as this used to - bounds the wrong quantity entirely.
      const int accel_raw = ((int)GET_BYTE(to_send, 0) << 8) | (int)GET_BYTE(to_send, 1);
      if ((accel_raw > CHANGAN_UNIT_ACCEL_MAX) || (accel_raw < CHANGAN_UNIT_ACCEL_MIN)) {
        tx = false;
      }
    } else {
      // Z6 / Z6 iDD: ACC_ACCTargetAcceleration bits [4..15], factor 0.05 m/s², signed 12-bit
      const int raw_accel_u = (int)(((GET_BYTE(to_send, 0) >> 4) | (GET_BYTE(to_send, 1) << 4)) & 0xFFFU);
      const int accel_cmd = (raw_accel_u & 0x800) ? (raw_accel_u - 0x1000) : raw_accel_u;
      if ((accel_cmd > CHANGAN_ACCEL_MAX) || (accel_cmd < CHANGAN_ACCEL_MIN)) {
        tx = false;
      }
    }
  }

  return tx;
}

// ── Safety hook: RX update ────────────────────────────────────────────────────
static void changan_rx_hook(const CANPacket_t *to_push) {
  (void)to_push;
}

// ── Safety hook: fwd ──────────────────────────────────────────────────────────
// Forward logic:
//   bus 0 (ESC/pt) → forward to bus 2 (MPC/cam): never (openpilot injects)
//   bus 2 (cam) → forward to bus 0 (ESC/pt): all except TX msgs intercepted by openpilot
//   bus 1 (MRR) → not forwarded
static bool changan_fwd_hook(int bus_num, int addr) {
  // return true to block forwarding
  bool block = false;

  if (bus_num == 2) {
    // Cam → pt: block messages that openpilot replaces
    block = ((addr == MSG_GW_1BA_TX) ||
             (addr == MSG_GW_244_TX) ||
             (addr == MSG_GW_307_TX) ||
             (addr == MSG_GW_31A_TX));
  } else if (bus_num == 0) {
    // pt → cam: block EPS relay (openpilot modifies and sends on bus 2)
    block = (addr == MSG_GW_17E);
  }

  return block;
}

// ── Safety model registration ─────────────────────────────────────────────────
const safety_hooks changan_hooks = {
  .init          = changan_init,
  .rx            = changan_rx_hook,
  .tx            = changan_tx_hook,
  .fwd           = changan_fwd_hook,
};
