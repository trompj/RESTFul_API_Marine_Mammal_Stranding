# Justin Tromp
# 05/02/2020
# Boat/Load API: Allows users to access boat data and manipulate data in a RESTful fashion. User may create a boat,
# edit a boat, and delete/view them respectively.

from google.cloud import datastore
from flask import Flask, request, jsonify, make_response
from google.oauth2 import id_token
import constants
from google.auth.transport import requests as google_req

app = Flask(__name__)
client = datastore.Client()

CLIENT_ID = '758294824537-q2dk9hqdt04s6r3nui1rdjs7j6cmqnmc.apps.googleusercontent.com'
CLIENT_SECRET = 'KFP6WvS7YbDDiJ_v-uZVDM5a'

# Check if boat name is unique given the name of the boat to be set and the client
def unique_boat_name(name, client, key):
    query = client.query(kind=constants.boat)
    query.add_filter('name', '=', name)

    results = list(query.fetch())

    # If no key provided, then entity isn't being updated
    if key == None:
        if len(results) == 0:
            return True
        else:
            return False

    # If a key is provided, then entity is being updated and must compare key if one entity is found. This will
    # allow the entity to set the same name if it has the same key value.
    else:
        if len(results) > 1:
            return False
        elif len(results) == 0:
            return True
        elif key == results[0].key:
            return True
        else:
            return False


# Check that fields match type restrictions for boat entity
def field_constraint_check(boat_content):
    fields_okay = True
    message_returned = ""

    for field in boat_content:
        # Ensure that name is less than 25 characters and is string
        if field == "name":
            if not isinstance(boat_content[field], str):
                fields_okay = False
            elif len(boat_content[field]) >= 25:
                fields_okay = False

        # Check that length is an integer and is less than 5000 feet
        elif field == "length":
            if not isinstance(boat_content[field], int):
                fields_okay = False
            elif boat_content[field] >= 5000:
                fields_okay = False

        # Check that type is a string and is less than 25 characters
        elif field == "type":
            if not isinstance(boat_content[field], str):
                fields_okay = False
            elif len(boat_content[field]) >= 25:
                fields_okay = False

        # Set error message to be returned and exit if encountered
        if not fields_okay:
            if field == "name":
                message_returned = "Invalid data provided: Name must be a string and less than 25 characters."
            elif field == "type":
                message_returned = "Invalid data provided: Type must be a string and less than 25 characters."
            elif field == "length":
                message_returned = "Invalid data provided: Length must be an integer and less than 5000."
            break

    return message_returned


# Check that JWT is valid and if not, return None, otherwise return sub value
def validate_authorization(req):
    bearer = request.headers.get('Authorization')

    # If authorization does not exist, throw 401
    if bearer == None:
        return None

    bearer = bearer.split(" ")

    try:
        # Verify that JWT is valid
        id_info = id_token.verify_oauth2_token(bearer[1], req, CLIENT_ID)
    except:
        # If invalid, set to None
        id_info = None

    if id_info == None:
        return None
    else:
        return id_info['sub']


# Get all boats and add a boat
@app.route('/boats', methods={'GET', 'POST'})
def boat_get_add():
    req = google_req.Request()

    # Add a boat with provided values in JSON
    if request.method == 'POST':
        # Check that request is JSON, if so continue, if not return
        if request.mimetype == "application/json":

            if request.accept_mimetypes != "application/json" and request.accept_mimetypes.accept_json != True:
                response = make_response(jsonify(Error="Content type to be returned can only be "
                                                       "application/json"))
                response.mimetype = "application/json"
                response.status_code = 406

                return response

            content = request.get_json()

            # Check if authorization is valid
            sub = validate_authorization(req)

            # If authorization does not exist or is invalid, throw 401
            if sub == None:
                response = make_response(jsonify(Error="Must provide a valid bearer token."))
                response.mimetype = "application/json"
                response.status_code = 401

                return response

            # Check that all three required JSON attributes are present
            if all([field in content.keys() for field in ['name', 'type', 'length']]):
                # Check that fields provided are correct types
                error_message = field_constraint_check(content)
                if error_message != "":
                    response = make_response(jsonify(Error=error_message))
                    response.mimetype = "application/json"
                    response.status_code = 400

                    return response

                # Check that name of boat is unique
                if not unique_boat_name(content['name'], client, None):
                    response = make_response(jsonify(Error="Boat already exists with name. Name must be unique."))
                    response.mimetype = "application/json"
                    response.status_code = 403

                    return response

                # Create a boat entity with given values
                new_boat = datastore.entity.Entity(key=client.key(constants.boat))
                new_boat.update({"name": content["name"], "type": content["type"],
                                 "length": content["length"], "owner": sub})

                # Send created boat to datastore
                client.put(new_boat)

                live_link = request.base_url + str(new_boat.id)
                # Set response
                boat = {
                    'id': new_boat.id,
                    'name': new_boat.get("name"),
                    'type': new_boat.get("type"),
                    'length': new_boat.get("length"),
                    'owner': sub,
                    'self': live_link
                }

                response = make_response(jsonify(boat))
                response.mimetype = "application/json"
                response.status_code = 201

                return response

            else:
                response = make_response(jsonify(Error="The request object is missing at least one of the required "
                                                       "attributes"))
                response.mimetype = "application/json"
                response.status_code = 400

                return response

        else:
            response = make_response(jsonify(Error="Can only accept application/json in request"))
            response.mimetype = "application/json"
            response.status_code = 415

            return response

    # Get all boats and output
    elif request.method == 'GET':
        query = client.query(kind=constants.boat)
        results = list(query.fetch())

        result_list = []
        for e in results:
            dict_result = dict(e)

            live_link = request.base_url + str(e.key.id)

            entity = {
                'id': e.key.id,
                'name': dict_result.get("name"),
                'type': dict_result.get("type"),
                'length': dict_result.get("length"),
                'owner': dict_result.get("owner"),
                'self': live_link
            }

            result_list.append(entity)
        return jsonify(result_list), 200

    # Incorrect request found
    else:
        response = make_response(jsonify(Error="Method not found"))
        response.mimetype = "application/json"
        response.status_code = 404

        return response


# Get a boat and delete a boat
@app.route('/boats/<id>', methods={'DELETE'})
def boat_get_delete_update(id):
    req = google_req.Request()

    # Create key based on ID for boat
    key = client.key(constants.boat, int(id))

    # Get boat based on key and update value(s)
    boat = client.get(key=key)

    # Check if authorization is valid
    sub = validate_authorization(req)

    # If authorization does not exist or is invalid, throw 401
    if sub == None:
        response = make_response(jsonify(Error="Must provide a valid bearer token."))
        response.mimetype = "application/json"
        response.status_code = 401

        return response

    # If the boat is not found and JWT is valid, return 403
    if boat == None:
        response = make_response(jsonify(Error="No boat with this ID exists"))
        response.mimetype = "application/json"
        response.status_code = 403

        return response

    # If the owner does not match the sub of authorization, then return no ID exists and 403
    elif boat['owner'] != sub:
        response = make_response(jsonify(Error="No boat with this ID exists"))
        response.mimetype = "application/json"
        response.status_code = 403

        return response

    # Delete a boat based on created key from ID
    if request.method == 'DELETE':

        # If boat exists, delete boat.
        if boat != None:
            client.delete(key)

            return '', 204

    # Incorrect request found
    else:
        return jsonify(Error='Method not accepted')


# Get all boats associated with owner_id
@app.route('/owners/<id>/boats', methods={'GET'})
def boat_owner_get(id):
    req = google_req.Request()

    # Check if authorization is valid
    sub = validate_authorization(req)

    # If authorization does not exist or is invalid, throw 401
    if sub == None:
        response = make_response(jsonify(Error="Must provide a valid bearer token."))
        response.mimetype = "application/json"
        response.status_code = 401

        return response

    # If the sub does not equal the provided owner ID, then return 401 as authorization does not match provided ID
    if sub != id:
        response = make_response(jsonify(Error="Owner ID does not match provided authorization."))
        response.mimetype = "application/json"
        response.status_code = 401

        return response

    # Check that id matches the sub by adding filter to only gather the boats from that owner
    query = client.query(kind=constants.boat)
    query.add_filter('owner', '=', id)

    results = list(query.fetch())

    result_list = []
    for e in results:
        dict_result = dict(e)

        live_link = request.base_url + str(e.key.id)

        entity = {
            'id': e.key.id,
            'name': dict_result.get("name"),
            'type': dict_result.get("type"),
            'length': dict_result.get("length"),
            'owner': dict_result.get("owner"),
            'self': live_link
        }

        result_list.append(entity)
    return jsonify(result_list), 200


if __name__ == '__main__':
    app.run(port=8080)
