# Changan UNI-T 2022 — opendbc 控车适配说明

## 对比分析结论

基于 CAN 日志与长安欧尚 Z6 DBC 的对比分析：

| 检查项 | 结果 |
|--------|------|
| 关键 ADAS CAN ID (0x17E/0x180/0x187/0x196/0x1BA/0x244/0x28B/0x28C/0x307/0x31A) | ✅ 完全一致 |
| 消息数据长度 | ✅ 完全一致（0x1BA/0x244=32B，0x307/0x31A=64B CAN-FD） |
| 总线拓扑 (bus0=pt, bus2=cam) | ⚠️ 日志显示 ADAS 命令消息仅在 bus0（网关中继），bus2 无持续消息 |
| GW_50/SRS (0x50) | ✅ UNIT 4 字节 |
| **档位消息 (0x39B)** | ✅ 已验证（byte5 bit5<<1\|bit0，P=0/R=1/N=2/D=3） |
| 转向/ACC CRC | ✅ **CRC-8 poly=0x1D init=0x6C**（46 万+帧验证；非 SAE-J1850 的 init=0xFF） |
| Rolling Counter | ✅ 各子消息 byte 低 4 位（48/112/176/240 位） |
| 转向角 GW_180 / 车速 GW_187 | ✅ Motorola 大端 16 位 |
| 转向命令 GW_1BA | ✅ byte2-4 大端 24 位，raw24 = 0x5DC200 + deg*10<<4 |

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
| `carcontroller.py` | 控车逻辑与 DBC 信号名解耦；仅 UNIT 的 AccTrqReq 改为正值（见修改日志） |
| `radar_interface.py` | 返回空，直接复用 |
| `can_crc.py` | ⚠️ 已修正 init=0x6C（见修改日志） |
| `changancan.py` | ⚠️ 已重构 0x1BA/0x244/0x307/0x31A/0x17E 中继（见修改日志） |

## 当前假设 & 待验证项

1. **✅ 档位消息 (GW_39B)：** 已通过 dangwei.csv 实车日志验证，0x39B 是档位消息，编码 = byte5 bit5<<1|bit0（P=0, R=1, N=2, D=3）。0x320 数据恒为 0，确认不是档位。

2. **✅ GW_50 (0x50)：** UNIT 日志 4 字节，DBC 定义为 4 字节；安全带信号 byte1 bit6 已验证。

3. **🟡 定速巡航按钮：** RES+/SET-/IACC 位已验证（byte0 bit4/bit6、byte1 bit4）；CANCEL 等其余按钮位需实车确认。

4. **🟡 0x244 ACC 命令：** 加速度 = byte0（0x64=100 即 0 m/s²，0.05/LSB）；AccTrqReq = byte12-13 小端正值。AccTrqReq 的 offset/gain 映射、ACCMode 语义需实车标定。

5. **🟡 总线拓扑：** 日志显示命令消息仅在 bus0（网关中继），bus2 无持续消息；已据此调整 carstate 与 safety。若实车 IACC 激活后 bus2 出现相机消息需重新评估。

6. **🔴 固件指纹 (fingerprints.py)：** 当前为空。需通过 panda 采集 ECU 固件版本后填入，openpilot 才能识别 UNIT 2022。

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
