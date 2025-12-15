# 🎳 ESP32 保齡球手部運動軌跡追蹤系統 (Bowling Trajectory Tracker)

> 一個基於 ESP32 與 MPU9255 的智慧型保齡球投球分析器，具備 3D 軌跡重建、最佳路徑比對與 AI 教練評分功能。

![Project Status](https://img.shields.io/badge/Status-Completed-green)
![Hardware](https://img.shields.io/badge/Hardware-ESP32__S3%20%2B%20MPU9255-blue)
![Language](https://img.shields.io/badge/Language-C%2B%2B%20%2F%20Python-orange)

## 📖 專案簡介 (Introduction)

本專案旨在解決保齡球初學者難以量化投球動作的問題。透過配戴式嵌入式裝置（ESP32 + IMU），捕捉手部揮動的加速度與角速度，並利用物理積分與演算法重建 3D 空間軌跡。

系統核心包含「**最佳路徑 (Golden Path)**」比對功能。透過 **Kabsch 演算法** 進行空間對齊，消除身高與站位差異，專注於分析「動作形狀」，並計算 MSE (均方誤差) 給予評分與具體的修正建議（如：手太低、往外推等）。

### ✨ 核心功能
* **即時數據採集**：使用 ESP32-S3 與 MPU9255 進行 100Hz 高頻採樣。
* **3D 軌跡視覺化**：透過 Python 繪製互動式 3D 投球路徑圖。
* **AI 虛擬教練**：
    * 自動分段分析（前段推球、中段擺盪、後段延伸）。
    * 提供文字化建議（例如：「手偏右了，請往內收」）。
* **動態標準設定**：可隨時將當前投球設定為新的「最佳路徑」。
* **智慧對齊演算法**：使用 Kabsch Algorithm 自動校正軌跡的旋轉與位移誤差。

---

## 🛠️ 硬體架構 (Hardware Setup)

| 元件 | 型號 / 規格 | 備註 |
| :--- | :--- | :--- |
| **Microcontroller** | ESP32-S3 Dev Module | 核心運算 |
| **IMU Sensor** | MPU9255 (9-Axis) | 加速度/陀螺儀/磁力計 |
| **Connection** | Micro USB | 供電與數據傳輸 |

### 接線圖 (Pinout)
本專案使用自定義 I2C 腳位（適用於 ESP32-S3）：

| MPU9255 Pin | ESP32-S3 Pin |
| :--- | :--- |
| VCC | 3.3V / 5V |
| GND | GND |
| **SCL** | **GPIO 21** |
| **SDA** | **GPIO 47** |

> ⚠️ **注意**：若使用不同型號開發板，請至 `Firmware` 程式碼中修改 `Wire.begin(SDA, SCL)` 設定。

---

## 🏗️ 系統設計 (System Architecture)

本系統開發過程採用標準系統分析方法：

1.  **IDEF0 功能模型分析**：
    * 定義系統輸入（物理運動）、控制（採樣率）、輸出（評分）與機制（演算法）。
    * 實現從 A0 (系統層) 到 A3 (評估層) 的細部拆解。
2.  **Grafcet 順序功能圖**：
    * 採用狀態機 (State Machine) 設計韌體邏輯。
    * 流程：`初始化` -> `待機` -> `錄製(練習/設定)` -> `運算` -> `評分`。

*(建議在此處放入你的 IDEF0 或 Grafcet 圖片)*

---

## 🚀 安裝與使用 (Installation & Usage)

### 1. 韌體端 (Firmware)
1.  安裝 **Arduino IDE**。
2.  安裝函式庫：`MPU9250` by **Hideaki Tai**。
3.  開啟 `Bowling_ESP32.ino`。
4.  確認 `I2C_SDA` 與 `I2C_SCL` 腳位設定正確。
5.  燒錄至 ESP32-S3。

### 2. 分析端 (Computer Analysis)
1.  安裝 Python 3.8+。
2.  安裝必要套件：
    ```bash
    pip install pandas numpy matplotlib pyserial
    ```
3.  修改 `main_analysis.py` 中的 `SERIAL_PORT` (例如 `COM3` 或 `/dev/ttyUSB0`)。

### 3. 開始操作
1.  連接 ESP32 至電腦。
2.  執行 Python 腳本：
    ```bash
    python main_analysis.py
    ```
3.  按一下 ESP32 上的 **BOOT 按鈕** 開始錄製，完成動作後再按一下停止。
4.  **建立標準**：第一次投球後，輸入 `y` 將其設為「最佳路徑」。
5.  **開始練習**：之後的投球，系統會自動計算 MSE 分數並給出建議。

---

## 🧮 演算法說明 (Algorithms)

### 1. 物理積分 (Physics Integration)
利用牛頓運動定律，將原始加速度數據進行兩次積分：

$$
a(t) \xrightarrow{\int} v(t) \xrightarrow{\int} p(t)
$$

*包含去重力補償 (Gravity Compensation) 以消除靜止偏差。*

### 2. 軌跡對齊 (Kabsch Algorithm)
為了公平比較兩次投球的形狀（忽略站位與握球角度差異），我們使用 SVD 分解計算最佳旋轉矩陣 $R$ 與位移向量 $t$，使：

$$
\min \sum \| (R \cdot P_{practice} + t) - P_{golden} \|^2
$$

### 3. 評分系統 (MSE Scoring)
計算對齊後的均方誤差 (Mean Squared Error)：
* **Score < 0.05**: 完美 (Perfect)
* **Score < 0.20**: 優秀 (Good)
* **Score > 0.20**: 需修正 (Needs Improvement)

---

## 📂 專案結構 (Folder Structure)

```text
Bowling_Tracker_Project/
├── Firmware/               # ESP32 Arduino 原始碼
│   └── Bowling_ESP32.ino
├── Analysis/               # Python 分析程式
│   ├── main_analysis.py    # 主程式 (含 GUI 繪圖與 AI 教練)
│   └── bowling_data/       # 自動產生的 CSV 數據與 PNG 圖表
└── README.md
