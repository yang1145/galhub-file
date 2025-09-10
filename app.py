import os
import sqlite3
import hashlib
import time
import bcrypt
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory, session
from werkzeug.utils import secure_filename
from datetime import datetime
from config import Config

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# 配置
UPLOAD_FOLDER = Config.UPLOAD_FOLDER
DATABASE = Config.DATABASE
MAX_FILE_SIZE = Config.MAX_CONTENT_LENGTH  # 4GB in bytes

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
    # 创建管理员表
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL)''')
    # 插入默认管理员账户 (用户名: admin, 密码: admin)
    c.execute("SELECT COUNT(*) FROM admins WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        # 使用bcrypt进行密码哈希
        password_hash = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())
        c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", 
                  ('admin', password_hash))
    conn.commit()
    conn.close()

# 计算文件哈希
def calculate_file_hash(filepath):
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# 检查是否已登录
def is_logged_in():
    return 'admin_id' in session

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
        username = request.form['username']
        password = request.form['password']
        
        # 验证管理员账户
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM admins WHERE username = ?', (username,))
        admin_record = c.fetchone()
        conn.close()
        
        if admin_record:
            admin_id, password_hash = admin_record
            # 验证密码 (注意：从数据库取出的hash需要是bytes类型)
            if isinstance(password_hash, str):
                password_hash = password_hash.encode('utf-8')
                
            if bcrypt.checkpw(password.encode('utf-8'), password_hash):
                session['admin_id'] = admin_id
                session['username'] = username
                flash('登录成功')
                return redirect(url_for('admin_panel'))
        
        flash('用户名或密码错误')
    
    return render_template('admin_login.html')

# 管理员登出
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('username', None)
    flash('已退出登录')
    return redirect(url_for('admin_login'))

# 管理员面板
@app.route('/admin')
def admin_panel():
    # 检查是否已登录
    if not is_logged_in():
        flash('请先登录')
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT id, filename, alias, upload_time FROM files ORDER BY timestamp DESC')
    files = c.fetchall()
    conn.close()
    return render_template('admin.html', files=files)

# 上传文件页面
@app.route('/admin/upload')
def upload_file_page():
    # 检查是否已登录
    if not is_logged_in():
        flash('请先登录')
        return redirect(url_for('admin_login'))
    
    return render_template('upload.html')

# 修改密码页面
@app.route('/admin/change_password', methods=['GET', 'POST'])
def change_password():
    # 检查是否已登录
    if not is_logged_in():
        flash('请先登录')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # 验证输入
        if not current_password or not new_password or not confirm_password:
            flash('请填写所有字段')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('新密码长度至少6位')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('新密码和确认密码不匹配')
            return render_template('change_password.html')
        
        # 验证当前密码
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT password_hash FROM admins WHERE id = ?', (session['admin_id'],))
        admin_record = c.fetchone()
        
        if admin_record:
            stored_password_hash = admin_record[0]
            # 确保存储的密码哈希是bytes类型
            if isinstance(stored_password_hash, str):
                stored_password_hash = stored_password_hash.encode('utf-8')
                
            if bcrypt.checkpw(current_password.encode('utf-8'), stored_password_hash):
                # 使用bcrypt更新密码
                new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                c.execute('UPDATE admins SET password_hash = ? WHERE id = ?', 
                          (new_password_hash, session['admin_id']))
                conn.commit()
                flash('密码修改成功')
                conn.close()
                return redirect(url_for('admin_panel'))
            else:
                flash('当前密码错误')
        else:
            flash('用户不存在')
        
        conn.close()
    
    return render_template('change_password.html')

# 上传文件
@app.route('/admin/upload', methods=['POST'])
def upload_file():
    # 检查是否已登录
    if not is_logged_in():
        flash('请先登录')
        return redirect(url_for('admin_login'))
    
    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('upload_file_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('upload_file_page'))
    
    if file:
        try:
            # 检查文件大小
            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            
            if file_length > MAX_FILE_SIZE:
                flash('文件太大，请上传小于4GB的文件')
                return redirect(url_for('upload_file_page'))
            
            filename = secure_filename(file.filename)
            alias = request.form.get('alias', '')
            
            # 检查文件是否已存在
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                flash('同名文件已存在，请先删除或重命名')
                return redirect(url_for('upload_file_page'))
            
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
        except Exception as e:
            flash(f'上传文件时出错: {str(e)}')
            # 如果保存失败，删除可能已创建的文件
            if os.path.exists(filepath):
                os.remove(filepath)
        
        return redirect(url_for('upload_file_page'))

# 删除文件
@app.route('/admin/delete/<int:file_id>')
def delete_file(file_id):
    # 检查是否已登录
    if not is_logged_in():
        flash('请先登录')
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT filename FROM files WHERE id = ?', (file_id,))
    file_record = c.fetchone()
    
    if file_record:
        filename = file_record[0]
        # 从文件系统删除文件
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # 从数据库删除记录
            c.execute('DELETE FROM files WHERE id = ?', (file_id,))
            conn.commit()
            flash('文件已删除')
        except Exception as e:
            flash(f'删除文件时出错: {str(e)}')
    else:
        flash('文件未找到')
    
    conn.close()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)