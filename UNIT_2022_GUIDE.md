# Changan UNI-T 2022 — opendbc 控车适配说明

## 对比分析结论

基于 CAN 日志与长安欧尚 Z6 DBC 的对比分析：

| 检查项 | 结果 |
|--------|------|
| 关键 ADAS CAN ID (0x17E/0x180/0x187/0x196/0x1BA/0x244/0x28B/0x28C/0x307/0x31A) | ✅ 完全一致 |
| 消息数据长度 | ✅ 完全一致 |
| 总线拓扑 (bus0=pt, bus2=cam) | ✅ 一致 |
| GW_50/SRS (0x50) | ⚠️ UNIT 仅 4 字节 (Z6 为 8 字节) |
| **档位消息 (0x338)** | ❌ UNIT 不存在，改用 0x39B (GW_39B) |
| 转向/ACC CRC 与 Rolling Counter | ✅ 遵循相同模式 (CRC-8/SAE-J1850) |

## 文件清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `opendbc/dbc/changan_unit_pt.dbc` | UNIT 2022 动力 CAN DBC（基于 Z6 DBC 调整） |
| `opendbc/dbc/changan_unit_can.dbc` | UNIT 2022 CAN 总线 DBC（对应 Z6 can DBC） |

### 修改文件
| 文件 | 变更 |
|------|------|
| `opendbc/car/changan/values.py` | 新增 `CHANGAN_UNI_T` 车型、`ChanganUnitPlatformConfig`、`CHANGAN_UNI_T_FLAG` |
| `opendbc/car/changan/fingerprints.py` | 添加 `CHANGAN_UNI_T` 空指纹占位 |
| `opendbc/car/changan/interface.py` | 注册 UNIT 安全模型参数 |
| `opendbc/car/changan/carstate.py` | 档位解析使用 `GW_39B` 替代 `GW_338` |
| `opendbc/safety/safety/safety_changan.h` | 添加 `CHANGAN_UNI_T_FLAG` 定义 |

### 无需修改（复用 Z6 代码）
| 文件 | 原因 |
|------|------|
| `changancan.py` | 信号名称与 DBC 一致，直接复用 |
| `carcontroller.py` | 控车逻辑与 DBC 信号名解耦，直接复用 |
| `can_crc.py` | CRC 算法完全相同 |
| `radar_interface.py` | 返回空，直接复用 |

## 当前假设 & 待验证项

1. **✅ 档位消息 (GW_39B)：** 已通过 dangwei.csv 实车日志验证，0x39B 是档位消息，编码 = byte5 bit5<<1|bit0（P=0, R=1, N=2, D=3）。0x320 数据恒为 0，确认不是档位。

2. **🟡 GW_50 (0x50)：** UNIT 日志显示 4 字节。DBC 定义为 8 字节但不影响解析（CANParser 会填充剩余字节）。

3. **🟡 定速巡航按钮：** 当前假设 UNIT 方向盘按键（RES+/SET-/CANCEL/iACC）信号布局与 Z6 一致。多数长安车型共用此布局。

4. **🔴 固件指纹 (fingerprints.py)：** 当前为空。需通过 panda 采集 ECU 固件版本后填入，openpilot 才能识别 UNIT 2022。

## 采集固件指纹的方法

```bash
# 连接 panda 后运行：
cd /data/openpilot
python selfdrive/debug/get_fw.py
# 将输出的固件版本填入 fingerprints.py
```

## 已知限制

- 未在实车上完整测试，所有信号解析基于 CAN 日志静态分析
- IACC/ELK/LKA 等高级辅助功能的 ACC Mode 值可能需要微调
- UNIT 2022 的转向比和轮胎刚度参数 (steerRatio/tireStiffnessFactor) 为估算值
