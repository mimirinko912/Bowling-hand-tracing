import serial
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os
from datetime import datetime

# ==========================================
# ⚙️ 參數設定區
# ==========================================
SERIAL_PORT = 'COM4'   # 請確認 Port
BAUD_RATE = 115200
DATA_FOLDER = 'bowling_data'
BEST_PATH_FILE = os.path.join(DATA_FOLDER, 'best_path.csv')

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# 物理參數
dt = 0.01
G_TO_MSS = 9.81

# ==========================================
# 🧮 演算法核心區
# ==========================================

def integrate_trajectory(df):
    """ 物理積分：加速度 -> 位置 """
    # 簡單去重力
    ax_offset = df['ax'].iloc[0:10].mean()
    ay_offset = df['ay'].iloc[0:10].mean()
    az_offset = df['az'].iloc[0:10].mean()

    df['ax_m'] = (df['ax'] - ax_offset) * G_TO_MSS
    df['ay_m'] = (df['ay'] - ay_offset) * G_TO_MSS
    df['az_m'] = (df['az'] - az_offset) * G_TO_MSS

    df['vx'] = df['ax_m'].cumsum() * dt
    df['vy'] = df['ay_m'].cumsum() * dt
    df['vz'] = df['az_m'].cumsum() * dt

    df['px'] = df['vx'].cumsum() * dt
    df['py'] = df['vy'].cumsum() * dt
    df['pz'] = df['vz'].cumsum() * dt
    return df

def rigid_transform_3D(A, B):
    """ Kabsch Algorithm: 計算最佳旋轉與位移 """
    assert A.shape == B.shape
    centroid_A = np.mean(A, axis=0)
    centroid_B = np.mean(B, axis=0)
    AA = A - centroid_A
    BB = B - centroid_B
    H = np.dot(AA.T, BB)
    U, S, Vt = np.linalg.svd(H)
    R = np.dot(Vt.T, U.T)
    if np.linalg.det(R) < 0:
        Vt[2, :] *= -1
        R = np.dot(Vt.T, U.T)
    t = centroid_B.T - np.dot(R, centroid_A.T)
    return R, t

def align_and_calculate_mse(current_df, best_df):
    """ 對齊並回傳: MSE分數, 對齊後的軌跡, 裁切後的最佳軌跡 """
    min_len = min(len(current_df), len(best_df))
    P = current_df[['px', 'py', 'pz']].iloc[:min_len].values
    G = best_df[['px', 'py', 'pz']].iloc[:min_len].values

    try:
        R, t = rigid_transform_3D(P, G)
        P_aligned = np.dot(P, R.T) + t.T
        mse = np.mean(np.sum((P_aligned - G)**2, axis=1))
        return mse, P_aligned, G # 多回傳一個 G 方便後續比較
    except Exception as e:
        print(f"對齊運算錯誤: {e}")
        return 999.0, P, G

# ==========================================
# 🗣️ AI 教練建議生成核心 (新增功能)
# ==========================================
def generate_coaching_advice(aligned_P, best_G):
    """
    根據對齊後的軌跡偏差，生成具體的教練建議
    """
    total_len = len(aligned_P)
    seg_len = total_len // 3

    # 定義偏差閥值 (單位: 公尺)
    # 例如 0.05 代表偏差超過 5公分 就會給建議
    THRESHOLD_X = 10
    THRESHOLD_Z = 10

    print("\n========= AI 分析報告 =========")

    # --- 1. 定義分段 ---
    segments = {
        "前段 (推球/下擺)": slice(0, seg_len),
        "中段 (擺盪最低點)": slice(seg_len, seg_len * 2),
        "後段 (出手/延伸)": slice(seg_len * 2, total_len)
    }

    for name, s_range in segments.items():
        # 計算該區段的平均誤差 (練習 - 最佳)
        # X軸: 正=偏右, 負=偏左 (假設 Y 是前進方向)
        diff_x = np.mean(aligned_P[s_range, 0] - best_G[s_range, 0])
        # Z軸: 正=偏高, 負=偏低
        diff_z = np.mean(aligned_P[s_range, 2] - best_G[s_range, 2])

        advice = []

        # X軸建議
        if diff_x > THRESHOLD_X: advice.append("❌ 手偏右了 (請往內收)")
        elif diff_x < -THRESHOLD_X: advice.append("❌ 手偏左了 (請往外推)")

        # Z軸建議
        if diff_z > THRESHOLD_Z: advice.append("❌ 手抬太高 (請壓低重心)")
        elif diff_z < -THRESHOLD_Z: advice.append("❌ 手太低了 (請抬高手臂)")

        if not advice:
            print(f"✅ [{name}]: 動作完美！")
        else:
            print(f"⚠️ [{name}]: {', '.join(advice)}")

    # --- 2. 延伸動作 (Follow-through) 特別分析 ---
    # 比較最後 10% 的 Z 軸斜率或高度差
    last_idx = int(total_len * 0.9)
    end_diff_z = aligned_P[-1, 2] - best_G[-1, 2]

    print("-" * 30)
    if end_diff_z < -0.1: # 如果結束點比最佳路徑低 10cm 以上
        print("[延伸建議]: 你的手太早放下來了！記得做完整的延伸 (Follow-through)，手要指著目標。")
    elif end_diff_z > 0.1:
        print("[延伸建議]: 最後手舉得有點太高，可能會影響控球。")
    else:
        print("[延伸建議]: 延伸動作做得很好，保持這個姿勢！")
    print("======================================\n")


def plot_3d_comparison(current_df, best_df=None, filename=None, title_extra=""):
    """ 繪製 3D 軌跡圖 """
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')

    ax.plot(current_df['px'], current_df['py'], current_df['pz'],
            label='Current (Aligned)', color='blue', linewidth=2)
    ax.scatter(current_df['px'].iloc[0], current_df['py'].iloc[0], current_df['pz'].iloc[0], c='g', s=50, label='Start')
    ax.scatter(current_df['px'].iloc[-1], current_df['py'].iloc[-1], current_df['pz'].iloc[-1], c='r', s=50, label='End')

    if best_df is not None:
        ax.plot(best_df['px'], best_df['py'], best_df['pz'],
                label='Golden Path', color='orange', linestyle='--', linewidth=2, alpha=0.6)

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title(f'Trajectory Analysis {title_extra}')
    ax.legend()

    if filename:
        plt.savefig(filename)
    plt.show()

# ==========================================
# 🚀 主程式
# ==========================================
def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ 連線成功 ({SERIAL_PORT})！")
    except Exception as e:
        print(f"❌ 連線失敗: {e}\n請檢查 ESP32 是否插入或 Port 設定錯誤。")
        return

    best_df = None
    if os.path.exists(BEST_PATH_FILE):
        print("📂 載入最佳路徑，啟用【AI 教練模式】。")
        try:
            best_df = pd.read_csv(BEST_PATH_FILE)
        except:
            print("⚠️ 最佳路徑檔讀取錯誤。")
    else:
        print("ℹ️ 尚未設定最佳路徑，目前為【自由錄製模式】。")

    print("\n👉 請按 ESP32 按鈕開始錄製...")
    buffer = []
    recording = False

    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()

            if line == "START_RECORDING":
                print("\n🔴 錄製中... (投球開始)")
                buffer = []
                recording = True

            elif line == "STOP_RECORDING":
                print("🟢 錄製結束，AI 分析中...")
                recording = False

                if len(buffer) < 10:
                    print("⚠️ 數據過少，忽略。")
                    continue

                columns = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
                valid_data = [x.split(',') for x in buffer if len(x.split(',')) == 6]
                if not valid_data: continue

                current_df = pd.DataFrame(valid_data, columns=columns).astype(float)
                current_df = integrate_trajectory(current_df)

                # 存檔
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = os.path.join(DATA_FOLDER, f"throw_{timestamp}.csv")
                current_df.to_csv(csv_filename, index=False)

                title_msg = ""

                # --- 🔥 核心修改：加入教練分析 ---
                if best_df is not None:
                    # 1. 對齊
                    mse_score, aligned_P, best_G = align_and_calculate_mse(current_df, best_df)
                    title_msg = f"(MSE: {mse_score:.2f})"

                    # 2. 生成文字建議 (新增功能)
                    generate_coaching_advice(aligned_P, best_G)

                    # 3. 更新數據以畫圖
                    min_len = len(aligned_P)
                    current_df_plot = current_df.copy()
                    current_df_plot.loc[:min_len-1, 'px'] = aligned_P[:, 0]
                    current_df_plot.loc[:min_len-1, 'py'] = aligned_P[:, 1]
                    current_df_plot.loc[:min_len-1, 'pz'] = aligned_P[:, 2]
                    current_df_plot = current_df_plot.iloc[:min_len]
                else:
                    current_df_plot = current_df

                # 畫圖
                png_filename = os.path.join(DATA_FOLDER, f"throw_{timestamp}.png")
                plot_3d_comparison(current_df_plot, best_df, png_filename, title_msg)

                # 使用者互動
                print("-" * 40)
                choice = input("⭐ 覺得這球是完美動作嗎？輸入 'y' 設為最佳路徑 (其他鍵跳過): ")
                if choice.lower() == 'y':
                    current_df.to_csv(BEST_PATH_FILE, index=False)
                    best_df = current_df
                    print("✅ 已更新「最佳路徑」！")
                print("-" * 40)

            elif recording and line:
                if ',' in line: buffer.append(line)

        except KeyboardInterrupt:
            print("\n程式結束")
            ser.close()
            break

if __name__ == "__main__":
    main()
