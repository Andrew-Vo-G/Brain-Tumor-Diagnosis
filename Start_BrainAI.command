#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==========================================="
echo "   Brain Tumor WebApp - Startup Script"
echo "==========================================="
echo "[1/5] Dọn dẹp các tiến trình bị kẹt..."
pkill -9 -f uvicorn > /dev/null 2>&1
sleep 1

echo "[2/5] Kiểm tra Môi trường Ảo (venv)..."
if [ ! -d "venv" ]; then
    echo ">> Đang tạo môi trường hệ thống cho lần chạy đầu tiên..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "[3/5] Tự động Cập nhật/Vá lỗi thư viện AI (Sẽ bỏ qua nếu mạng lỗi)..."
pip install -q -r requirements.txt > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo ">> (Hệ thống tiếp tục khởi động...)"
fi

echo "[4/5] Chạy máy chủ AI và nạp dữ liệu (Sẽ mất khoảng 10-15s)..."
PRELOAD_AI_ASYNC=1 FAST_INFERENCE=1 YOLO_OFFLINE=1 uvicorn backend.main:app --host 0.0.0.0 --port 8000 --loop asyncio &
UVICORN_PID=$!

echo "Đang chờ máy chủ trí tuệ nhân tạo (AI) sẵn sàng..."
until curl -s http://127.0.0.1:8000/ > /dev/null; do
    if ! kill -0 $UVICORN_PID 2>/dev/null; then
        echo "❌ LỖI NGHIÊM TRỌNG: Máy chủ Uvicorn đã bị sập đột ngột trong lúc Nạp AI!"
        echo "Hãy đảm bảo bạn không mở file này 2 lần cùng 1 lúc."
        exit 1
    fi
    sleep 2
done

echo "[5/5] Khởi động hoàn tất! Đang mở trình duyệt..."
open "http://localhost:8000"

echo ""
echo "🔥 WebApp đã NẠP XONG! Tốc độ phân tích lúc này là dưới 1 giây."
echo "🛑 LƯU Ý QUAN TRỌNG: Không đóng cửa sổ màu đen này trong quá trình làm việc, nếu đóng webapp sẽ sập."
echo "Để tắt server, quay lại đây và bấm tổ hợp phím [Ctrl + C]."
wait $UVICORN_PID
