import os
import sqlite3
import hashlib
import time
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# 配置
UPLOAD_FOLDER = 'files'
DATABASE = 'files.db'
MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB in bytes

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保文件上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT NOT NULL,
                  alias TEXT,
                  upload_time TEXT NOT NULL,
                  timestamp INTEGER NOT NULL,
                  file_hash TEXT NOT NULL)''')
    conn.commit()
    conn.close()

# 计算文件哈希
def calculate_file_hash(filepath):
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# 主页 - 文件列表
@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT id, filename, alias, upload_time FROM files ORDER BY timestamp DESC')
    files = c.fetchall()
    conn.close()
    return render_template('index.html', files=files)

# 下载页面
@app.route('/download/<int:file_id>')
def download(file_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT filename, alias FROM files WHERE id = ?', (file_id,))
    file_record = c.fetchone()
    conn.close()
    
    if file_record:
        filename, alias = file_record
        return render_template('download.html', id=file_id, filename=filename, alias=alias)
    else:
        flash('文件未找到')
        return redirect(url_for('index'))

# 实际下载文件
@app.route('/files/<int:file_id>')
def serve_file(file_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT filename FROM files WHERE id = ?', (file_id,))
    file_record = c.fetchone()
    conn.close()
    
    if file_record:
        filename = file_record[0]
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    else:
        flash('文件未找到')
        return redirect(url_for('index'))

# 管理员登录页面
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        # 简单密码验证 (实际应用中应该使用更安全的方法)
        if password == 'admin':  # 请在生产环境中更改此密码
            return redirect(url_for('admin_panel'))
        else:
            flash('密码错误')
    
    return render_template('admin_login.html')

# 管理员面板
@app.route('/admin')
def admin_panel():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT id, filename, alias, upload_time FROM files ORDER BY timestamp DESC')
    files = c.fetchall()
    conn.close()
    return render_template('admin.html', files=files)

# 上传文件
@app.route('/admin/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('admin_panel'))
    
    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('admin_panel'))
    
    if file:
        # 检查文件大小
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        
        if file_length > MAX_FILE_SIZE:
            flash('文件太大，请上传小于4GB的文件')
            return redirect(url_for('admin_panel'))
        
        filename = secure_filename(file.filename)
        alias = request.form.get('alias', '')
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 计算文件哈希
        file_hash = calculate_file_hash(filepath)
        
        # 获取当前时间
        upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        timestamp = int(time.time())
        
        # 保存到数据库
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('INSERT INTO files (filename, alias, upload_time, timestamp, file_hash) VALUES (?, ?, ?, ?, ?)',
                  (filename, alias, upload_time, timestamp, file_hash))
        conn.commit()
        conn.close()
        
        flash('文件上传成功')
        return redirect(url_for('admin_panel'))

# 删除文件
@app.route('/admin/delete/<int:file_id>')
def delete_file(file_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT filename FROM files WHERE id = ?', (file_id,))
    file_record = c.fetchone()
    
    if file_record:
        filename = file_record[0]
        # 从文件系统删除文件
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # 从数据库删除记录
        c.execute('DELETE FROM files WHERE id = ?', (file_id,))
        conn.commit()
    
    conn.close()
    flash('文件已删除')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)