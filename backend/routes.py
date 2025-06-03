import base64
from flask import render_template, request, redirect, url_for, flash, Blueprint, session
import service
import os
from models  import User, Project, db
# from werkzeug.security import check_password_hash
from datetime import datetime

# Создание Blueprint для маршрутов
routes_bp = Blueprint('routes', __name__)

# Check if app is behind proxy
behind_proxy = os.getenv('BEHIND_PROXY', 'false').lower() == 'true'
prefix = '/plan-fact' if behind_proxy else ''

DOLLAR = float(os.getenv('DOLLAR', 13050))
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER') # Можно указать абсолютный путь, например, os.path.join(app.root_path, 'uploads')
ALLOWED_EXTENSIONS = {'xlsx'}

# Helper function to create correct URLs with prefix
def make_url(endpoint):
    """Create a URL with the correct prefix when behind a proxy"""
    if behind_proxy:
        # Direct URL construction with prefix
        if endpoint.startswith('/'):
            return prefix + endpoint
        else:
            return prefix + '/' + endpoint
    return endpoint

def decode_header_full_name(request):
    """
    Декодирует base64-закодированное полное имя из заголовков запроса
    
    Args:
        request: Объект запроса Flask с заголовками
        
    Returns:
        str: Декодированное полное имя или оригинальное значение, если не закодировано
    """
    # Получаем закодированное имя и флаг кодировки
    encoded_full_name = request.headers.get('X-User-Full-Name', '')
    encoding = request.headers.get('X-User-Full-Name-Encoding', '')
    
    print(f"Received full name header: {encoded_full_name}, encoding: {encoding}")
    
    if encoding == 'base64' and encoded_full_name:
        try:
            # Декодируем base64
            decoded_bytes = base64.b64decode(encoded_full_name)
            decoded_name = decoded_bytes.decode('utf-8')
            print(f"Decoded name: '{decoded_name}'")
            return decoded_name
        except Exception as e:
            print(f"Error decoding full name: {e}")
            return encoded_full_name  # Возвращаем как есть, если декодирование не удалось
    else:
        return encoded_full_name  # Не закодировано или нет указания кодировки


def get_current_user():
    """Get current user information from request headers"""
    # Получение имени пользователя из заголовка аутентификации
    username = request.headers.get('X-User-Name')
    # Поиск пользователя в базе данных
    user = User.query.filter_by(login=username).first()
    
    is_admin = request.headers.get('X-User-Admin', 'false').lower() == 'true'
    full_name = decode_header_full_name(request)

    role_str = request.headers.get('X-User-Roles')
    roles = str.split(role_str, ',')
    role=''
    if 'admin' in roles or 'plan-fact-admin' in roles:
        role = 'admin'
    elif 'plan-fact-user' in roles or 'user' in roles:
        role = 'user'
    if user:
        if user.role != 'admin' and is_admin:
            user.role = 'admin'
            db.session.commit()
    print(f"User found: {user}, is_admin: {is_admin}")
    # Если пользователь не найден, но у него есть доступ через шлюз (т.е. заголовок X-User-Name присутствует),
    # создаем нового пользователя в базе данных
    if not user and username:
        # Получаем дополнительную информацию из заголовков и декодируем Base64 если нужно
        full_name = decode_header_full_name(request)
        
        # Создаем нового пользователя с декодированным полным именем
        user = User(
            login=username,
            full_name=full_name,
            role = role,
        )
        db.session.add(user)
        
    if user and ( user.full_name!=full_name):
        user.full_name = full_name
    if user and (user.role != role):
        user.role = role
    try:
        db.session.commit()  # This should set the user.id
    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {str(e)}")
    return user
  

@routes_bp.route('/')
def main():
    """Main route for the application."""
    # Get all projects
    projects = Project.query.all()
    month = projects[0].data_update if projects else "Обновите для получения данных"
    user = get_current_user()  # Ensure user is set in service
    try:
        file_path = os.path.join('./excel_data/database.xlsx')
        if os.path.exists(file_path):
            file_updated = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            file_updated = "File not found"
    except Exception as e:
        file_updated = f"Error: {str(e)}"
    
    # Get last_count from session or use default
    last_count = session.get('last_count', 3)
    
    # Pass the projects and prefix info to the template
    return render_template('main.html', projects=projects, month=month, file_updated=file_updated, last_count=last_count, prefix=prefix, current_user=user)  # Add prefix to template

@routes_bp.route('/update-database', methods=['POST'])
def update_database():
    if request.method == 'POST':
        # Получаем значение из формы по имени поля ('last_count')
        last_count_str = request.form.get('last_count')

        # Преобразуем в число, с значением по умолчанию, если что-то пошло не так
        try:
            last_count = int(last_count_str) if last_count_str else 3 # По умолчанию 3, если пусто
            if last_count < 1: # Добавим проверку минимального значения
                last_count = 1
        except (ValueError, TypeError):
            last_count = 3 # По умолчанию 3 при ошибке преобразования

        flash(f'Запущено обновление данных с last_count = {last_count}...', 'info')
        try:
            # Вызываем вашу функцию get_data с полученным значением
            service.get_data(last_house_count=last_count)
            flash('Обновление данных завершено.', 'success')
            # Сохраняем значение в сессию, чтобы оно отобразилось в input при перезагрузке
            session['last_count'] = last_count
        except Exception as e:
            flash(f'Ошибка при обновлении данных: {e}', 'error')
            # Можно оставить старое значение или сбросить
            session['last_count'] = session.get('last_count', 3) # Оставляем старое или 3

        # Перенаправляем пользователя обратно на главную страницу
        return redirect(make_url('/'))

    # Если метод не POST (хотя route настроен только на POST), просто перенаправляем
    return redirect(make_url('/'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@routes_bp.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # Debugging information
        print(f"Received upload request. Content length: {request.content_length} bytes")
        
        # Check max file size before processing
        max_file_size = 100 * 1024 * 1024  # 100MB
        if request.content_length > max_file_size:
            flash(f'File too large. Maximum allowed size is 100MB.', 'error')
            return redirect('/plan-fact/')
            
        # Проверяем, есть ли файл в запросе
        if 'xlsx_file' not in request.files:
            flash('No file part', 'error')
            return redirect('/plan-fact/')  # Absolute path with prefix
            
        file = request.files['xlsx_file']

        # Если пользователь не выбрал файл, браузер может отправить
        # пустую часть без имени файла
        if file.filename != 'database.xlsx':
            flash('Bad file name! The file must have name "database.xlsx" double check it, then upload.', 'danger')
            return redirect('/plan-fact/')

        # Проверяем, что файл существует и имеет разрешенное расширение
        if file and allowed_file(file.filename):
            filename = file.filename

            # Создаем папку для загрузок, если она не существует
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            # Сохраняем файл в указанную папку
            try:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                flash(f'File "{filename}" uploaded successfully!', 'success')
                # Здесь вы можете добавить логику для обработки файла (например, чтение данных)
                # process_xlsx_file(file_path)
            except Exception as e:
                 flash(f'An error occurred while saving the file: {e}', 'error')

            # Redirect to main page with absolute path
            return redirect('/plan-fact/')  # Absolute path with prefix

    # GET requests on /upload not handled, redirect
    return redirect('/plan-fact/')  # Absolute path with prefix

@routes_bp.route('/debug')
def debug():
    """Debug endpoint to show path information and static file URLs."""
    from flask import request, url_for, current_app
    
    static_url = url_for('static', filename='style.css')
    main_url = url_for('routes.main')
    
    debug_info = {
        'APPLICATION_ROOT': current_app.config.get('APPLICATION_ROOT'),
        'static_url_path': current_app.static_url_path,
        'url_for_static': static_url,
        'url_for_main': main_url,
        'request_path': request.path,
        'request_script_root': request.script_root,
        'request_url_rule': str(request.url_rule) if request.url_rule else None,
        'request_base_url': request.base_url,
        'request_url': request.url,
    }
    
    return debug_info

@routes_bp.route('/test-static')
def test_static():
    """Return a simple HTML page that tests static file loading."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Static File Test</title>
        <link rel="stylesheet" href="/plan-fact/static/style.css">
    </head>
    <body>
        <h1>Static File Test</h1>
        <p>If you see this text in green with a border, the CSS loaded correctly.</p>
        <div class="status">
            <pre>Path: {path}</pre>
        </div>
    </body>
    </html>
    """.format(path=request.path)
    return html

# Если есть аналогичные обработчики заголовков в этом сервисе:
# Replace any code that gets the full name header with:
# full_name = decode_header_full_name(request)
