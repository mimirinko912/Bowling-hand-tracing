/*
 * 專案：保齡球軌跡追蹤系統 (Final Version)
 * 硬體：ESP32-S3 + MPU9255
 * 腳位：SDA=47, SCL=21 (已驗證成功)
 * 函式庫：MPU9250 by Hideaki Tai
 */
#include "MPU9250.h"
#include <Wire.h>

MPU9250 mpu;

// --- 🔥 硬體腳位設定 (根據你剛測通的結果) ---
const int I2C_SDA = 37;
const int I2C_SCL = 36;
const int BUTTON_PIN = 0;  // ESP32 上面的 BOOT 按鈕
const int LED_PIN = 2;     // 狀態指示燈 (若沒亮可能是腳位不同，但不影響功能)

// --- 系統變數 ---
bool isRecording = false;
unsigned long lastSampleTime = 0;
const int SAMPLE_INTERVAL = 10; // 10ms = 100Hz 採樣率

void setup() {
    Serial.begin(115200);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    pinMode(LED_PIN, OUTPUT);

    // 1. 啟動 I2C (這就是你剛剛測試成功的關鍵！)
    Wire.begin(I2C_SDA, I2C_SCL);
    delay(2000);

    // 2. 初始化 MPU
    Serial.println("Initializing MPU...");
    if (!mpu.setup(0x68)) {  
        Serial.println("MPU connection failed!");
        while (1) {
            // 失敗時快閃 LED
            digitalWrite(LED_PIN, HIGH); delay(100);
            digitalWrite(LED_PIN, LOW); delay(100);
        }
    }
    
    // 開機成功，慢閃 3 下
    for(int i=0; i<3; i++) {
        digitalWrite(LED_PIN, HIGH); delay(300);
        digitalWrite(LED_PIN, LOW); delay(300);
    }
    Serial.println("SYSTEM_READY");
}

void loop() {
    // 🔥 重要：這個函式庫要求每次 loop 都要呼叫 update() 才能更新數據
    if (mpu.update()) {
        
        // --- 1. 按鈕控制邏輯 (Grafcet 狀態切換) ---
        if (digitalRead(BUTTON_PIN) == LOW) {
            delay(300); // 防彈跳
            isRecording = !isRecording; // 切換錄製狀態
            
            if (isRecording) {
                Serial.println("START_RECORDING"); // 告訴 Python 開始
                digitalWrite(LED_PIN, HIGH);       // 亮燈
            } else {
                Serial.println("STOP_RECORDING");  // 告訴 Python 結束
                digitalWrite(LED_PIN, LOW);        // 滅燈
            }
        }

        // --- 2. 錄製與傳輸 (Data Transmission) ---
        if (isRecording) {
            if (millis() - lastSampleTime >= SAMPLE_INTERVAL) {
                lastSampleTime = millis();
                
                // 傳送格式：Ax,Ay,Az,Gx,Gy,Gz
                // 注意：這各函式庫回傳單位是 g (重力) 和 degree/s (角速度)
                // 我們之後在 Python 端再轉成 m/s^2 方便計算
                Serial.print(mpu.getAccX()); Serial.print(",");
                Serial.print(mpu.getAccY()); Serial.print(",");
                Serial.print(mpu.getAccZ()); Serial.print(",");
                Serial.print(mpu.getGyroX()); Serial.print(",");
                Serial.print(mpu.getGyroY()); Serial.print(",");
                Serial.println(mpu.getGyroZ());
            }
        }
    }
}