from flask import Flask, request, make_response, jsonify
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError # Import IntegrityError for database errors
from datetime import datetime # Import datetime for timestamps

from models import db, Bakery, BakedGood

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False # Ensure JSON output is not compacted, for readability

migrate = Migrate(app, db)

db.init_app(app)

# Custom error handler for 404 Not Found
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Resource not found"}), 404)

# Custom error handler for 405 Method Not Allowed
@app.errorhandler(405)
def method_not_allowed(error):
    return make_response(jsonify({"error": "Method not allowed"}), 405)

# Custom error handler for 400 Bad Request
@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({"error": "Bad request"}), 400)


@app.route('/')
def home():
    return '<h1>Bakery GET-POST-PATCH-DELETE API</h1>'

# GET /bakeries: returns a list of JSON objects for all bakeries in the database.
@app.route('/bakeries', methods=['GET'])
def bakeries():
    bakeries = [bakery.to_dict() for bakery in Bakery.query.all()]
    return make_response(bakeries, 200)

# GET and PATCH /bakeries/<int:id>
# GET: returns a single bakery as JSON with its baked goods nested in a list.
# PATCH: updates the name of the bakery in the database and returns its data as JSON.
@app.route('/bakeries/<int:id>', methods=['GET', 'PATCH'])
def bakery_by_id(id):
    bakery = Bakery.query.filter_by(id=id).first()

    # If bakery not found, return 404
    if not bakery:
        return not_found(f"Bakery with id {id} not found")

    if request.method == 'GET':
        bakery_serialized = bakery.to_dict()
        return make_response(bakery_serialized, 200)

    elif request.method == 'PATCH':
        # Use request.form to get data sent as form-urlencoded (e.g., from test_client().patch with 'data' parameter)
        data = request.form 

        # Validate if data is provided and contains 'name'
        if not data or 'name' not in data:
            return bad_request("Missing 'name' field in request body for update")

        bakery.name = data['name']
        bakery.updated_at = datetime.utcnow() # Update timestamp

        try:
            db.session.add(bakery) # Add the modified object to the session
            db.session.commit() # Commit changes to the database
            bakery_serialized = bakery.to_dict()
            return make_response(bakery_serialized, 200) # Return updated bakery data
        except IntegrityError:
            db.session.rollback()
            return make_response(jsonify({"error": "Name must be unique"}), 400)
        except Exception as e:
            db.session.rollback() # Rollback in case of other errors
            return make_response(jsonify({"error": f"Failed to update bakery: {str(e)}"}), 500)


# GET /baked_goods/by_price: returns a list of baked goods as JSON, sorted by price in descending order.
@app.route('/baked_goods/by_price', methods=['GET'])
def baked_goods_by_price():
    baked_goods_by_price = BakedGood.query.order_by(BakedGood.price.desc()).all()
    baked_goods_by_price_serialized = [
        bg.to_dict() for bg in baked_goods_by_price
    ]
    return make_response(baked_goods_by_price_serialized, 200)
    
# GET /baked_goods/most_expensive: returns the single most expensive baked good as JSON.
@app.route('/baked_goods/most_expensive', methods=['GET'])
def most_expensive_baked_good():
    most_expensive = BakedGood.query.order_by(BakedGood.price.desc()).limit(1).first()
    
    # If no baked good is found, return 404
    if not most_expensive:
        return not_found("No baked goods found")

    most_expensive_serialized = most_expensive.to_dict()
    return make_response(most_expensive_serialized, 200)

# POST /baked_goods: creates a new baked good in the database and returns its data as JSON.
@app.route('/baked_goods', methods=['POST'])
def create_baked_good():
    # Use request.form to get data sent as form-urlencoded (e.g., from test_client().post with 'data' parameter)
    data = request.form 

    # Validate required fields
    if not data or not all(k in data for k in ('name', 'price', 'bakery_id')):
        return bad_request("Missing required fields: name, price, bakery_id")

    name = data['name']
    
    # Convert price to float, handle potential ValueError
    try:
        price = float(data['price'])
    except ValueError:
        return bad_request("Price must be a valid number")

    # Convert bakery_id to int, handle potential ValueError
    try:
        bakery_id = int(data['bakery_id'])
    except ValueError:
        return bad_request("Bakery ID must be a valid integer")

    # Check if bakery_id exists
    bakery = Bakery.query.get(bakery_id)
    if not bakery:
        return not_found(f"Bakery with id {bakery_id} not found")

    try:
        # Create a new BakedGood instance
        new_baked_good = BakedGood(name=name, price=price, bakery_id=bakery_id)
        db.session.add(new_baked_good) # Add to session
        db.session.commit() # Commit to database

        # Return new baked good with 201 Created status
        return make_response(new_baked_good.to_dict(), 201)
    except IntegrityError:
        db.session.rollback()
        return make_response(jsonify({"error": "Baked good name must be unique"}), 400)
    except Exception as e:
        db.session.rollback() # Rollback in case of error
        return make_response(jsonify({"error": f"Failed to create baked good: {str(e)}"}), 500)

# DELETE /baked_goods/<int:id>: deletes the baked good from the database and returns a JSON message.
@app.route('/baked_goods/<int:id>', methods=['DELETE'])
def delete_baked_good(id):
    baked_good = BakedGood.query.filter_by(id=id).first() # Get baked good

    # If baked good not found, return 404
    if not baked_good:
        return not_found(f"Baked good with id {id} not found")

    try:
        db.session.delete(baked_good) # Delete from session
        db.session.commit() # Commit to database

        # Return success message with 200 OK status
        return make_response(jsonify({"message": f"Baked good with id {id} successfully deleted"}), 200)
    except Exception as e:
        db.session.rollback() # Rollback in case of error
        return make_response(jsonify({"error": f"Failed to delete baked good: {str(e)}"}), 500)


if __name__ == '__main__':
    app.run(port=5555, debug=True)
