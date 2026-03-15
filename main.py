import os
from src.ui.app import create_app

if __name__ == '__main__':
    app = create_app()
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("=" * 60)
    print("🧪 气体传感器数据分析软件 v1.0")
    print("=" * 60)
    print("🌐 访问: http://localhost:5000")
    print("📁 上传Excel文件开始分析")
    print("=" * 60)
    app.run(debug=debug, host='0.0.0.0', port=5000)
