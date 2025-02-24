import os
import docker
import time
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, PasswordField, SelectMultipleField, IntegerField, widgets
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
# Absoluter Pfad: Da der WORKDIR in der Dockerfile /app ist, wird die DB unter /app/data/docker_controller.db angelegt
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/docker_controller.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Persistente Daten (Datenbank & Icons) werden im Ordner "data" abgelegt
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'data', 'icons')

db = SQLAlchemy(app)
client = docker.from_env()

# Route, um Dateien aus dem data-Ordner (z.B. Icons) bereitzustellen
@app.route('/data/<path:filename>')
def data_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'data'), filename)

# --------------------------------------------------------------------
# Model for many-to-many relationship with extra attributes (for groups)
# --------------------------------------------------------------------
class GroupContainer(db.Model):
    __tablename__ = 'group_container'
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'), primary_key=True)
    startup_order = db.Column(db.Integer, default=0)
    delay = db.Column(db.Integer, default=0)  # Delay in seconds
    container = db.relationship("Container", back_populates="group_assocs")
    group = db.relationship("Group", back_populates="group_containers")

# ---------------------------
# Models
# ---------------------------
class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Internal name
    display_name = db.Column(db.String(100), nullable=False)        # Display name (z.B. "Nextcloud")
    docker_name = db.Column(db.String(100), nullable=False)         # Actual Docker container name
    icon = db.Column(db.String(200), nullable=True)                 # z.B. "icons/filename.png"
    order_index = db.Column(db.Integer, default=0)                  # Ordering for standalone containers
    group_assocs = db.relationship("GroupContainer", back_populates="container", cascade="all, delete-orphan", lazy='joined')

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)    # Group name
    icon = db.Column(db.String(200), nullable=True)                 # Group icon
    order_index = db.Column(db.Integer, default=0)                  # Ordering for groups
    group_containers = db.relationship("GroupContainer", back_populates="group", cascade="all, delete-orphan", lazy='joined')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')   # "admin" oder "user"
    containers = db.relationship("Container", secondary="user_container", backref="users")
    api_key = db.Column(db.String(128), nullable=True)  # Benutzer-spezifischer API-Key

user_container = db.Table('user_container',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('container_id', db.Integer, db.ForeignKey('container.id'), primary_key=True)
)

# ---------------------------
# Flask-Login configuration
# ---------------------------
login_manager = LoginManager(app)
login_manager.login_view = 'login_view'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------
# Forms
# ---------------------------
class ContainerForm(FlaskForm):
    name = StringField('Internal Name', validators=[DataRequired()])
    display_name = StringField('Display Name', validators=[DataRequired()])
    docker_name = StringField('Docker Container Name', validators=[DataRequired()])
    icon = FileField('Icon (optional)', validators=[FileAllowed(['jpg','jpeg','png','gif'], 'Only image files allowed')])
    submit = SubmitField('Save')

# Hier wird das Container-Feld als Checkbox-Liste dargestellt
class GroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired()])
    icon = FileField('Group Icon (optional)', validators=[FileAllowed(['jpg','jpeg','png','gif'], 'Only image files allowed')])
    containers = SelectMultipleField('Containers', coerce=int, widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput())
    submit = SubmitField('Create Group')

# Login-Formular
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Hier auch Checkboxen für die Container-Auswahl (benutzerverwaltung)
class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password')
    role = StringField('Role (admin/user)', validators=[DataRequired()])
    containers = SelectMultipleField('Accessible Containers', coerce=int, widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput())
    submit = SubmitField('Save')

class ContainerOrderForm(FlaskForm):
    submit = SubmitField('Save')

class GroupOrderForm(FlaskForm):
    submit = SubmitField('Save')

# ---------------------------
# API Endpoints
# ---------------------------

# API: Steuert einen einzelnen Container
@app.route('/api/control', methods=['POST'])
def api_control():
    data = request.get_json()
    username = data.get('username')
    api_key = data.get('api_key')
    container_id = data.get('container_id')
    action = data.get('action')
    if not all([username, api_key, container_id, action]):
        return jsonify({"error": "Missing parameters"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or user.api_key != api_key:
        return jsonify({"error": "Invalid credentials or API key"}), 401
    container = Container.query.get(container_id)
    if not container:
        return jsonify({"error": "Container not found"}), 404
    # Unabhängig von Admin, wird immer geprüft, ob der Container in der Benutzerzuordnung enthalten ist
    if container not in user.containers:
        return jsonify({"error": "Access denied to this container"}), 403
    try:
        docker_cont = client.containers.get(container.docker_name)
        if action == "start":
            docker_cont.start()
        elif action == "stop":
            docker_cont.stop()
        else:
            return jsonify({"error": "Invalid action"}), 400
    except docker.errors.NotFound:
        return jsonify({"error": f"Container {container.docker_name} not found"}), 404
    return jsonify({"status": "success", "container": container.display_name, "action": action})

# API: Gibt den Status eines einzelnen Containers zurück
@app.route('/api/status', methods=['GET'])
def api_status():
    username = request.args.get('username')
    api_key = request.args.get('api_key')
    container_id = request.args.get('container_id')
    if not all([username, api_key, container_id]):
        return jsonify({"error": "Missing parameters"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or user.api_key != api_key:
        return jsonify({"error": "Invalid credentials or API key"}), 401
    container = Container.query.get(container_id)
    if not container:
        return jsonify({"error": "Container not found"}), 404
    if container not in user.containers:
        return jsonify({"error": "Access denied to this container"}), 403
    try:
        docker_cont = client.containers.get(container.docker_name)
        status = docker_cont.status
    except docker.errors.NotFound:
        status = "not found"
    return jsonify({"container_id": container.id, "container_name": container.display_name, "status": status})

# API: Steuert alle Container einer Gruppe
@app.route('/api/control_group', methods=['POST'])
def api_control_group():
    data = request.get_json()
    username = data.get('username')
    api_key = data.get('api_key')
    group_id = data.get('group_id')
    action = data.get('action')
    if not all([username, api_key, group_id, action]):
        return jsonify({"error": "Missing parameters"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or user.api_key != api_key:
        return jsonify({"error": "Invalid credentials or API key"}), 401
    group = Group.query.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    # Prüfe, ob alle Container der Gruppe dem Benutzer zugeordnet sind
    if not all(gc.container in user.containers for gc in group.group_containers):
        return jsonify({"error": "Access denied to this group"}), 403
    errors = {}
    for gc in group.group_containers:
        try:
            docker_cont = client.containers.get(gc.container.docker_name)
            if action == "start":
                docker_cont.start()
            elif action == "stop":
                docker_cont.stop()
            else:
                return jsonify({"error": "Invalid action"}), 400
        except docker.errors.NotFound:
            errors[gc.container.id] = f"Container {gc.container.docker_name} not found"
    if errors:
        return jsonify({"status": "partial success", "errors": errors})
    return jsonify({"status": "success", "group": group.name, "action": action})

# API: Gibt den Status einer Gruppe zurück
@app.route('/api/group_status', methods=['GET'])
def api_group_status():
    username = request.args.get('username')
    api_key = request.args.get('api_key')
    group_id = request.args.get('group_id')
    if not all([username, api_key, group_id]):
        return jsonify({"error": "Missing parameters"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or user.api_key != api_key:
        return jsonify({"error": "Invalid credentials or API key"}), 401
    group = Group.query.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    if not all(gc.container in user.containers for gc in group.group_containers):
        return jsonify({"error": "Access denied to this group"}), 403
    total = len(group.group_containers)
    running = 0
    statuses = {}
    for gc in group.group_containers:
        try:
            docker_cont = client.containers.get(gc.container.docker_name)
            st = docker_cont.status
            statuses[gc.container.id] = st
            if st == 'running':
                running += 1
        except docker.errors.NotFound:
            statuses[gc.container.id] = "not found"
    return jsonify({
        "group_id": group.id,
        "group_name": group.name,
        "status": f"{running}/{total}",
        "container_statuses": statuses
    })

# ---------------------------
# New Route: Generate API Key for a User (Admin UI)
# ---------------------------
@app.route('/admin/users/<int:user_id>/generate_api_key', methods=['GET'])
@login_required
def generate_api_key_for_user(user_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('admin_users_view'))
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_users_view'))
    new_key = secrets.token_hex(16)
    user.api_key = new_key
    db.session.commit()
    flash("New API key generated for user.", "success")
    return redirect(url_for('admin_edit_user_view', user_id=user_id))

# ---------------------------
# Normal Routes (UI)
# ---------------------------
@app.route('/login_view', methods=['GET', 'POST'])
def login_view():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout_view')
@login_required
def logout_view():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login_view'))

@app.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        all_containers = Container.query.order_by(Container.order_index).all()
        individual_containers = [c for c in all_containers if len(c.group_assocs) == 0]
        groups = Group.query.order_by(Group.order_index).all()
    else:
        allowed_containers = current_user.containers
        all_groups = Group.query.join(Group.group_containers).filter(
            GroupContainer.container_id.in_([c.id for c in allowed_containers])
        ).all()
        full_groups = [g for g in all_groups if all(gc.container in allowed_containers for gc in g.group_containers.all())]
        union_full = set()
        for g in full_groups:
            for gc in g.group_containers.all():
                union_full.add(gc.container)
        individual_containers = sorted([c for c in allowed_containers if c not in union_full], key=lambda x: x.order_index)
        groups = full_groups

    container_status = {}
    for cont in individual_containers:
        try:
            docker_cont = client.containers.get(cont.docker_name)
            status = docker_cont.status
        except docker.errors.NotFound:
            status = "not found"
        container_status[cont.id] = status

    group_status = {}
    group_container_status = {}
    for group in groups:
        total = len(group.group_containers)
        running = 0
        gc_status = {}
        for gc in sorted(group.group_containers, key=lambda x: x.startup_order):
            try:
                docker_cont = client.containers.get(gc.container.docker_name)
                st = docker_cont.status
                if st == 'running':
                    running += 1
            except docker.errors.NotFound:
                st = "not found"
            gc_status[gc.container.id] = st
        group_status[group.id] = f"{running}/{total}"
        group_container_status[group.id] = gc_status

    return render_template('index.html',
                           individual_containers=individual_containers,
                           groups=groups,
                           container_status=container_status,
                           group_status=group_status,
                           group_container_status=group_container_status)

@app.route('/control', methods=['POST'])
@login_required
def control_view():
    cont_id = request.form.get('container_id')
    action = request.form.get('action')
    cont = Container.query.get(cont_id)
    if cont:
        try:
            docker_cont = client.containers.get(cont.docker_name)
            if action == "start":
                docker_cont.start()
            elif action == "stop":
                docker_cont.stop()
        except docker.errors.NotFound:
            flash(f"Container {cont.docker_name} not found.", "danger")
    return redirect(url_for('index'))

@app.route('/control_group', methods=['POST'])
@login_required
def control_group_view():
    group_id = request.form.get('group_id')
    action = request.form.get('action')
    group = Group.query.get(group_id)
    if group:
        for gc in sorted(group.group_containers, key=lambda x: x.startup_order):
            try:
                docker_cont = client.containers.get(gc.container.docker_name)
                if action == "start":
                    docker_cont.start()
                    if gc.delay:
                        time.sleep(gc.delay)
                elif action == "stop":
                    docker_cont.stop()
            except docker.errors.NotFound:
                flash(f"Container {gc.container.docker_name} not found.", "danger")
    return redirect(url_for('index'))

# --- Container Management ---
@app.route('/container/new', methods=['GET', 'POST'])
@login_required
def new_container_view():
    if current_user.role != 'admin':
        flash("Only admins can create containers.", "danger")
        return redirect(url_for('index'))
    form = ContainerForm()
    if form.validate_on_submit():
        icon_filename = None
        if form.icon.data:
            file = form.icon.data
            filename = secure_filename(file.filename)
            upload_folder = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            file.save(os.path.join(upload_folder, filename))
            icon_filename = f'icons/{filename}'
        container = Container(
            name=form.name.data,
            display_name=form.display_name.data,
            docker_name=form.docker_name.data,
            icon=icon_filename
        )
        db.session.add(container)
        try:
            db.session.commit()
            flash('Container added.', "success")
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash("Error: Container name already exists.", "danger")
    return render_template('new_container.html', form=form)

@app.route('/container/edit/<int:container_id>', methods=['GET', 'POST'])
@login_required
def edit_container_view(container_id):
    if current_user.role != 'admin':
        flash("Only admins can edit containers.", "danger")
        return redirect(url_for('index'))
    cont = Container.query.get(container_id)
    if not cont:
        flash('Container not found.', "danger")
        return redirect(url_for('index'))
    form = ContainerForm(obj=cont)
    if form.validate_on_submit():
        cont.name = form.name.data
        cont.display_name = form.display_name.data
        cont.docker_name = form.docker_name.data
        if form.icon.data:
            file = form.icon.data
            filename = secure_filename(file.filename)
            upload_folder = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            file.save(os.path.join(upload_folder, filename))
            cont.icon = f'icons/{filename}'
        db.session.commit()
        flash('Container updated.', "success")
        return redirect(url_for('index'))
    return render_template('edit_container.html', form=form, container=cont)

@app.route('/container/delete/<int:container_id>', methods=['POST'])
@login_required
def delete_container_view(container_id):
    if current_user.role != 'admin':
        flash("Only admins can delete containers.", "danger")
        return redirect(url_for('index'))
    cont = Container.query.get(container_id)
    if cont:
        db.session.delete(cont)
        db.session.commit()
        flash('Container deleted.', "success")
    return redirect(url_for('index'))

# --- Route for ordering standalone containers ---
@app.route('/container/order', methods=['GET', 'POST'])
@login_required
def container_order_view():
    if current_user.role != 'admin':
        flash("Only admins can change the order.", "danger")
        return redirect(url_for('index'))
    containers = Container.query.order_by(Container.order_index).all()
    if request.method == 'POST':
        for cont in containers:
            try:
                new_order = int(request.form.get(f'order_{cont.id}', cont.order_index))
            except (ValueError, TypeError):
                new_order = cont.order_index
            cont.order_index = new_order
        db.session.commit()
        flash("Container order updated.", "success")
        return redirect(url_for('index'))
    return render_template('container_order.html', containers=containers)

# --- Group Management ---
@app.route('/group/new', methods=['GET', 'POST'])
@login_required
def new_group_view():
    if current_user.role != 'admin':
        flash("Only admins can create groups.", "danger")
        return redirect(url_for('index'))
    form = GroupForm()
    form.containers.choices = [(c.id, c.display_name) for c in Container.query.all()]
    if form.validate_on_submit():
        group = Group(name=form.name.data)
        if form.icon.data:
            file = form.icon.data
            filename = secure_filename(file.filename)
            upload_folder = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            file.save(os.path.join(upload_folder, filename))
            group.icon = f'icons/{filename}'
        for idx, cont_id in enumerate(form.containers.data):
            container = Container.query.get(cont_id)
            if container:
                gc = GroupContainer(startup_order=idx, delay=0, container=container)
                group.group_containers.append(gc)
        db.session.add(group)
        db.session.commit()
        flash('Group created.', "success")
        return redirect(url_for('index'))
    return render_template('new_group.html', form=form)

@app.route('/group/delete/<int:group_id>', methods=['POST'])
@login_required
def delete_group_view(group_id):
    if current_user.role != 'admin':
        flash("Only admins can delete groups.", "danger")
        return redirect(url_for('index'))
    group = Group.query.get(group_id)
    if group:
        db.session.delete(group)
        db.session.commit()
        flash('Group deleted.', "success")
    return redirect(url_for('index'))

@app.route('/group/order/<int:group_id>', methods=['GET', 'POST'])
@login_required
def group_order_view(group_id):
    group = Group.query.get(group_id)
    if not group:
        flash("Group not found.", "danger")
        return redirect(url_for('index'))
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        for gc in group.group_containers:
            try:
                new_order = int(request.form.get(f'order_{gc.container.id}', gc.startup_order))
                new_delay = int(request.form.get(f'delay_{gc.container.id}', gc.delay))
            except (ValueError, TypeError):
                new_order = gc.startup_order
                new_delay = gc.delay
            gc.startup_order = new_order
            gc.delay = new_delay
        db.session.commit()
        flash("Group order updated.", "success")
        return redirect(url_for('index'))
    group_containers = sorted(group.group_containers, key=lambda x: x.startup_order)
    return render_template('group_order.html', group=group, group_containers=group_containers)

@app.route('/group/order_all', methods=['GET', 'POST'])
@login_required
def group_order_all_view():
    if current_user.role != 'admin':
        flash("Only admins can change group order.", "danger")
        return redirect(url_for('index'))
    groups = Group.query.order_by(Group.order_index).all()
    if request.method == 'POST':
        for group in groups:
            try:
                new_order = int(request.form.get(f'order_{group.id}', group.order_index))
            except (ValueError, TypeError):
                new_order = group.order_index
            group.order_index = new_order
        db.session.commit()
        flash("Group order updated.", "success")
        return redirect(url_for('index'))
    return render_template('group_order_all.html', groups=groups)

# --- Admin User Management ---
@app.route('/admin/users', methods=['GET'])
@login_required
def admin_users_view():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
def new_user_view():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('index'))
    form = UserForm()
    form.containers.choices = [(c.id, c.display_name) for c in Container.query.all()]
    if form.validate_on_submit():
        if not form.password.data:
            flash("Password is required for new users.", "danger")
            return render_template('new_user.html', form=form)
        user = User(
            username=form.username.data,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data
        )
        for cont_id in form.containers.data:
            container = Container.query.get(cont_id)
            if container:
                user.containers.append(container)
        db.session.add(user)
        db.session.commit()
        flash('User created.', "success")
        return redirect(url_for('admin_users_view'))
    return render_template('new_user.html', form=form)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user_view(user_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('index'))
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_users_view'))
    form = UserForm(obj=user)
    form.containers.choices = [(c.id, c.display_name) for c in Container.query.all()]
    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        user.role = form.role.data
        user.containers = []
        for cont_id in form.containers.data:
            container = Container.query.get(cont_id)
            if container:
                user.containers.append(container)
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for('admin_users_view'))
    return render_template('admin_edit_user.html', form=form, user=user)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user_view(user_id):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('index'))
    user = User.query.get(user_id)
    if user:
        # Prevent deletion if this is the only admin or if current admin is deleting themselves.
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1 or user.id == current_user.id:
                flash("You cannot delete the only admin or yourself.", "danger")
                return redirect(url_for('admin_users_view'))
        db.session.delete(user)
        db.session.commit()
        flash("User deleted.", "success")
    else:
        flash("User not found.", "danger")
    return redirect(url_for('admin_users_view'))

# ---------------------------
# Create admin user from environment variables (update if exists)
# ---------------------------
def create_admin_from_config():
    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if admin_username and admin_password:
        admin = User.query.filter_by(role='admin').first()
        if admin:
            if admin.username != admin_username or not check_password_hash(admin.password_hash, admin_password):
                admin.username = admin_username
                admin.password_hash = generate_password_hash(admin_password)
                db.session.commit()
                print("Admin user updated from environment variables.")
        else:
            admin = User(
                username=admin_username,
                password_hash=generate_password_hash(admin_password),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user '{admin_username}' created from environment variables.")
    else:
        print("ADMIN_USERNAME and ADMIN_PASSWORD are not set.")

# ---------------------------
# Run the application
# ---------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_from_config()
    app.run(host='0.0.0.0', port=5000)
