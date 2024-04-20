from flask import Flask, request, jsonify
from flask_graphql import GraphQLView
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from keycloak import KeycloakOpenID
from flask_cors import CORS
# Initialize Flask app
app = Flask(__name__)
CORS(app)
# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Define Todo model
class TodoModel(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    time = db.Column(db.DateTime)
    images = db.Column(db.String(100))  # Assuming the images are stored as file paths


# Define Todo GraphQL Object Type
class Todo(graphene.ObjectType):
    id = graphene.Int()
    title = graphene.String()
    description = graphene.String()
    time = graphene.DateTime()

# Define Query for GraphQL
class Query(graphene.ObjectType):
    todos = SQLAlchemyConnectionField(Todo)

# Define Mutation for GraphQL
class CreateTodo(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String()
        time = graphene.DateTime()

    todo = graphene.Field(Todo)

    def mutate(self, info, title, description=None, time=None):
        todo = TodoModel(title=title, description=description, time=time)
        db.session.add(todo)
        db.session.commit()
        return CreateTodo(todo=todo)

class Mutation(graphene.ObjectType):
    create_todo = CreateTodo.Field()

# Initialize GraphQL schema
schema = graphene.Schema(query=Query, mutation=Mutation)

# Configure Keycloak
keycloak_openid = KeycloakOpenID(server_url="https://your-keycloak-domain/auth/",
                                 client_id="your-client-id",
                                 realm_name="your-realm-name",
                                 client_secret_key="your-client-secret")


# Flask route to list all To-Dos
@app.route('/todos', methods=['GET'])
def get_todos():
    todos = TodoModel.query.all()
    return jsonify([{
        'id': todo.id,
        'title': todo.title,
        'description': todo.description,
        'time': todo.time,
        'images': todo.images
    } for todo in todos])

# Flask route to add a To-Do
@app.route('/todos', methods=['POST'])
def add_todo():
    data = request.get_json()
    new_todo = TodoModel(
        title=data['title'],
        description=data['description'],
        time=data['time'],
        images=data.get('images')  # Optional, only if provided
    )
    db.session.add(new_todo)
    db.session.commit()
    return jsonify({'message': 'Todo added successfully'}), 201

# Flask route to delete a To-Do
@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    todo = TodoModel.query.get(todo_id)
    if not todo:
        return jsonify({'error': 'Todo not found'}), 404
    db.session.delete(todo)
    db.session.commit()
    return jsonify({'message': 'Todo deleted successfully'})

# Flask route to edit a To-Do
@app.route('/todos/<int:todo_id>', methods=['PUT'])
def edit_todo(todo_id):
    todo = TodoModel.query.get(todo_id)
    if not todo:
        return jsonify({'error': 'Todo not found'}), 404
    data = request.get_json()
    todo.title = data.get('title', todo.title)
    todo.description = data.get('description', todo.description)
    todo.time = data.get('time', todo.time)
    todo.images = data.get('images', todo.images)
    db.session.commit()
    return jsonify({'message': 'Todo updated successfully'})


# Flask route for login
@app.route('/login')
def login():
    return keycloak_openid.authorization_url()

# Flask route for callback after login
@app.route('/callback')
def callback():
    code = request.args.get('code')
    token = keycloak_openid.token(code)
    user_info = keycloak_openid.userinfo(token['access_token'])
    # Here you can store user_info in session or database for authentication
    return jsonify(token)

# Flask route for logout
@app.route('/logout')
def logout():
    # Implement logout functionality here
    return "Logged out successfully"

# Flask route for GraphQL endpoint
app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

if __name__ == '__main__':
    app.run(debug=True)
