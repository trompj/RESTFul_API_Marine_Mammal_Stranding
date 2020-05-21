# Justin Tromp
# 05/02/2020
# Boat/Load API: Allows users to access boat data and manipulate data in a RESTful fashion. User may create a boat,
# edit a boat, and delete/view them respectively.

from google.cloud import datastore
from flask import Flask, request, jsonify, make_response
import flask
import requests
import uuid
import json
from datetime import datetime, timedelta
from google.oauth2 import id_token
import constants
from google.auth.transport import requests as google_req

app = Flask(__name__)
client = datastore.Client()

CLIENT_ID = '758294824537-q2dk9hqdt04s6r3nui1rdjs7j6cmqnmc.apps.googleusercontent.com'
CLIENT_SECRET = 'KFP6WvS7YbDDiJ_v-uZVDM5a'
SCOPE = 'profile email openid'
# REDIRECT_URI = 'https://trompj-assignment-7.wl.r.appspot.com/user_info'
REDIRECT_URI = 'http://localhost:8080/user_info'

app.secret_key = b'_5#y2L"F4Q88z\n\xec]/'


# Check latitude for valid values. If not, return False. Otherwise, return True.
def valid_lat(latitude):
    if latitude < -90 or latitude > 90:
        return False

    else:
        return True


# Check latitude for valid values. If not, return False. Otherwise, return True.
def valid_long(longitude):
    if longitude < -180 or longitude > 180:
        return False

    else:
        return True


# def unique_boat_name(name, client, key):
#     query = client.query(kind=constants.boat)
#     query.add_filter('name', '=', name)
#
#     results = list(query.fetch())
#
#     # If no key provided, then entity isn't being updated
#     if key == None:
#         if len(results) == 0:
#             return True
#         else:
#             return False
#
#     # If a key is provided, then entity is being updated and must compare key if one entity is found. This will
#     # allow the entity to set the same name if it has the same key value.
#     else:
#         if len(results) > 1:
#             return False
#         elif len(results) == 0:
#             return True
#         elif key == results[0].key:
#             return True
#         else:
#             return False


# Check that fields match type restrictions for stranding entity and return corresponding error message
def field_constraint_check(stranding_content, is_mammal):
    fields_okay = True
    message_returned = ""

    for field in stranding_content:
        # Ensure that latitude is float or int value and is a valid range
        if field == "latitude" and not is_mammal:
            if not isinstance(stranding_content[field], float) and not isinstance(stranding_content[field], int):
                fields_okay = False
            elif not valid_lat(stranding_content[field]):
                fields_okay = False

        # Ensure that longitude is float or int value and is a valid range
        elif field == "longitude" and not is_mammal:
            if not isinstance(stranding_content[field], float) and not isinstance(stranding_content[field], int):
                fields_okay = False
            elif not valid_long(stranding_content[field]):
                fields_okay = False

        # Check that type is a string and is less than or equal to 150 characters
        elif field == "note":
            if not isinstance(stranding_content[field], str):
                fields_okay = False
            elif len(stranding_content[field]) > 150:
                fields_okay = False

        # Check that alive is boolean type
        elif field == "alive" and is_mammal:
            if not isinstance(stranding_content[field], bool):
                fields_okay = False

        # Check that alive is boolean type
        elif field == "species" and is_mammal:
            if not isinstance(stranding_content[field], str):
                fields_okay = False
            elif len(stranding_content[field]) > 40:
                fields_okay = False

        # Set error message to be returned and exit if encountered
        if not fields_okay:
            if field == "note":
                message_returned = "Invalid data provided: Note must be a string and less than or equal to 150 " \
                                   "characters."
            elif field == "longitude":
                message_returned = "Invalid data provided: Longitude must be a float or integer and must be within the" \
                                   " range of -180 through 180."
            elif field == "latitude":
                message_returned = "Invalid data provided: Latitude must be a float or integer and must be within the" \
                                   " range of -90 through 90."
            elif field == "alive":
                message_returned = "Invalid data provided: Alive must be a boolean type."

            elif field == "species":
                message_returned = "Invalid data provided: Species must be a string type and less than or equal to 40" \
                                   " characters."
            break

    return message_returned


# Check that JWT is valid and if not, return None, otherwise return sub value
def validate_authorization(req):
    # bearer = request.headers.get('Authorization')
    #
    # # If authorization does not exist, throw 401
    # if bearer == None:
    #     return None
    #
    # bearer = bearer.split(" ")
    #
    # try:
    #     # Verify that JWT is valid
    #     id_info = id_token.verify_oauth2_token(bearer[1], req, CLIENT_ID)
    # except:
    #     # If invalid, set to None
    #     id_info = None
    #
    # if id_info == None:
    #     return None
    # else:
    #     return id_info['sub']
    return "213213"


# Get all strandings and add a stranding. Strandings added will have empty arrays of mammals and an empty responder.
@app.route('/strandings', methods={'GET', 'POST'})
def stranding_get_add():
    req = google_req.Request()

    # Add a stranding with provided values in JSON
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
            if all([field in content.keys() for field in ['longitude', 'latitude', 'note']]):
                # Check that fields provided are correct types
                error_message = field_constraint_check(content, False)
                if error_message != "":
                    response = make_response(jsonify(Error=error_message))
                    response.mimetype = "application/json"
                    response.status_code = 400

                    return response

                if content['note'] is None:
                    note = ""
                else:
                    note = content['note']

                # Create a stranding entity with given values
                new_stranding = datastore.entity.Entity(key=client.key(constants.strandings))
                new_stranding.update({"longitude": content["longitude"], "latitude": content["latitude"],
                                      "note": note, "responder": "", "mammals": []})

                # Send created stranding to datastore
                client.put(new_stranding)

                live_link = request.base_url + str(new_stranding.id)
                # Set response
                stranding = {
                    'id': new_stranding.id,
                    'longitude': new_stranding.get("longitude"),
                    'latitude': new_stranding.get("latitude"),
                    'note': new_stranding.get("note"),
                    'responder': "",
                    'mammals': [],
                    'self': live_link
                }

                response = make_response(jsonify(stranding))
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
        query = client.query(kind=constants.strandings)
        results = list(query.fetch())

        result_list = []
        for e in results:
            dict_result = dict(e)

            live_link = request.base_url + str(e.key.id)

            entity = {
                'id': e.key.id,
                'longitude': dict_result.get("longitude"),
                'latitude': dict_result.get("latitude"),
                'note': dict_result.get("note"),
                'responder': dict_result.get("responder"),
                'mammals': dict_result.get("mammals"),
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


# Get a stranding, edit a stranding, or delete a stranding
@app.route('/strandings/<id>', methods={'GET', 'DELETE', 'PATCH', 'PUT'})
def stranding_delete_update(id):
    req = google_req.Request()

    # Create key based on ID for stranding
    key = client.key(constants.strandings, int(id))

    # Get stranding based on key and update value(s)
    stranding = client.get(key=key)

    # Check if authorization is valid
    sub = validate_authorization(req)

    # If authorization does not exist or is invalid, throw 401
    if sub == None:
        response = make_response(jsonify(Error="Must provide a valid bearer token."))
        response.mimetype = "application/json"
        response.status_code = 401

        return response

    # If the stranding is not found and JWT is valid, return 403
    if stranding == None:
        response = make_response(jsonify(Error="No stranding with this ID exists"))
        response.mimetype = "application/json"
        response.status_code = 403

        return response

    # If the owner does not match the sub of authorization, then return no ID exists and 403
    # elif stranding['responder'] != sub:
    #     response = make_response(jsonify(Error="No stranding with this ID exists"))
    #     response.mimetype = "application/json"
    #     response.status_code = 403
    #
    #     return response

    # Find stranding with created key
    if request.method == 'GET':
        # Create query
        query = client.query(kind=constants.strandings)
        query.key_filter(key, '=')

        # Return found result
        result = list(query.fetch())

        # If an entity is found, return it
        if len(result) == 1:

            dict_result = dict(result[0])

            live_link = request.base_url
            # Set response
            response = {
                'id': id,
                'longitude': dict_result.get("longitude"),
                'latitude': dict_result.get("latitude"),
                'note': dict_result.get("note"),
                'responder': dict_result.get("responder"),
                'mammals': dict_result.get("mammals"),
                'self': live_link
            }

            # Add self link for each mammal
            for mammal in response.get("mammals"):
                mammal_url = request.host_url + "mammals"
                mammal["self"] = mammal_url + "/" + str(mammal.get("id"))

            return jsonify(response), 200

        # No entity found, return not found
        else:
            return jsonify(Error="No stranding with this ID exists"), 404

    # Delete a stranding based on created key from ID
    elif request.method == 'DELETE':
        # If stranding exists, delete stranding.
        if stranding != None:

            # If there are responder active on the stranding, remove each responder
            if stranding.get('responder') != "":
                responder = stranding.get('responder')

                # Create key based on ID for mammal and get mammal
                key = client.key(constants.responders, int(responder.get('id')))
                responder = client.get(key=key)

                stranding_list = []
                # Loop through each stranding in responder list and add all except entity being deleted
                for stranding in responder.get('strandings'):
                    if stranding.get('id') != id:
                        stranding_list.append(stranding)

                # Update responder with stranding list that no longer has the stranding being deleted
                responder.update({"strandings": stranding_list})
                client.put(responder)

            # If there are mammals associated with the stranding, remove stranding from each mammal.
            if stranding.get('mammals') != []:
                # Loop through list of mammals
                for mammal in stranding.get('mammals'):
                    # Create key based on ID for mammal and get mammal
                    mammal_key = client.key(constants.mammals, int(mammal.get('id')))
                    mammal = client.get(key=mammal_key)

                    # Update stranding to empty for mammal
                    mammal.update({"stranding": ""})
                    client.put(mammal)

            client.delete(key)

            return '', 204

    # Update stranding information based on created key
    elif request.method == 'PATCH':
        content = request.get_json()

        # Check that fields provided are correct types
        error_message = field_constraint_check(content, False)
        if error_message != "":
            response = make_response(jsonify(Error=error_message))
            response.mimetype = "application/json"
            response.status_code = 400

            return response

        # If the stranding is not found, return 404
        if stranding == None:
            return jsonify(Error="No stranding with this stranding ID exists"), 404

        # Loop through fields that were updated in JSON and update on stranding
        for field in content:
            stranding.update({field: content[field]})

        client.put(stranding)

        live_link = request.base_url + str(stranding.get('id'))
        # Set response
        response = {
            'id': stranding.key.id,
            'longitude': stranding.get("longitude"),
            'latitude': stranding.get("latitude"),
            'note': stranding.get("note"),
            'responder': stranding.get("responder"),
            'mammals': stranding.get("mammals"),
            'self': live_link

        }

        response = make_response(jsonify(response))
        response.mimetype = "application/json"
        response.status_code = 200

        return response

    # Update stranding information based on created key
    elif request.method == 'PUT':
        content = request.get_json()

        # Check if all required attributes are passed to edit stranding
        if all([field in content.keys() for field in ['longitude', 'latitude', 'note']]):
            # Check that fields provided are correct types
            error_message = field_constraint_check(content, False)
            if error_message != "":
                response = make_response(jsonify(Error=error_message))
                response.mimetype = "application/json"
                response.status_code = 400

                return response

            # If the stranding is not found, return 404
            if stranding == None:
                return jsonify(Error="No stranding with this stranding ID exists"), 404

            # Loop through fields that were updated in JSON and update on stranding
            for field in content:
                stranding.update({field: content[field]})

            client.put(stranding)

            live_link = request.base_url + str(stranding.get('id'))
            # Set response
            response = {
                'id': stranding.key.id,
                'longitude': stranding.get("longitude"),
                'latitude': stranding.get("latitude"),
                'note': stranding.get("note"),
                'responder': stranding.get("responder"),
                'mammals': stranding.get("mammals"),
                'self': live_link

            }

            response = make_response(jsonify(response))
            response.mimetype = "application/json"
            response.status_code = 200

            return response

        else:
            response = make_response(jsonify(Error="The request object is missing at least one of the required "
                                                   "attributes"))
            response.mimetype = "application/json"
            response.status_code = 400

            return response

    # Incorrect request found
    else:
        return jsonify(Error='Method not accepted')


# Get all mammals and add a mammal. Mammals added will not be assigned to a stranding initially.
@app.route('/mammals', methods={'GET', 'POST'})
def mammal_get_add():
    req = google_req.Request()

    # Add a mammal with provided values in JSON
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
            if all([field in content.keys() for field in ['species', 'alive', 'note']]):
                # Check that fields provided are correct types
                error_message = field_constraint_check(content, True)
                if error_message != "":
                    response = make_response(jsonify(Error=error_message))
                    response.mimetype = "application/json"
                    response.status_code = 400

                    return response

                if content['note'] is None:
                    note = ""
                else:
                    note = content['note']

                # Create a mammal entity with given values
                new_mammal = datastore.entity.Entity(key=client.key(constants.mammals))
                new_mammal.update({"species": content["species"], "alive": content["alive"],
                                      "note": note, "stranding": ""})

                # Send created mammal to datastore
                client.put(new_mammal)

                live_link = request.base_url + str(new_mammal.id)
                # Set response
                mammal = {
                    'id': new_mammal.id,
                    'species': new_mammal.get("species"),
                    'alive': new_mammal.get("alive"),
                    'note': new_mammal.get("note"),
                    'stranding': new_mammal.get("stranding"),
                    'self': live_link
                }

                response = make_response(jsonify(mammal))
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

    # Get all mammals and output
    elif request.method == 'GET':
        query = client.query(kind=constants.mammals)
        results = list(query.fetch())

        result_list = []
        for e in results:
            dict_result = dict(e)

            live_link = request.base_url + str(e.key.id)

            entity = {
                'id': e.key.id,
                'species': dict_result.get("species"),
                'alive': dict_result.get("alive"),
                'note': dict_result.get("note"),
                'stranding': dict_result.get("stranding"),
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


# Get a mammal, edit a mammal, or delete a mammal
@app.route('/mammals/<id>', methods={'GET', 'DELETE', 'PATCH', 'PUT'})
def mammal_get_delete_update(id):
    req = google_req.Request()

    # Create key based on ID for stranding
    key = client.key(constants.mammals, int(id))

    # Get stranding based on key and update value(s)
    mammal = client.get(key=key)

    # Check if authorization is valid
    sub = validate_authorization(req)

    # If authorization does not exist or is invalid, throw 401
    if sub == None:
        response = make_response(jsonify(Error="Must provide a valid bearer token."))
        response.mimetype = "application/json"
        response.status_code = 401

        return response

    # If the mammal is not found and JWT is valid, return 403
    if mammal == None:
        response = make_response(jsonify(Error="No mammal with this ID exists"))
        response.mimetype = "application/json"
        response.status_code = 403

        return response

    # If the owner does not match the sub of authorization, then return no ID exists and 403
    # elif mammal['responder'] != sub:
    #     response = make_response(jsonify(Error="No mammal with this ID exists"))
    #     response.mimetype = "application/json"
    #     response.status_code = 403
    #
    #     return response

    # Find mammal with created key
    if request.method == 'GET':
        dict_result = dict(mammal)

        live_link = request.base_url
        # Set response
        response = {
            'id': id,
            'species': dict_result.get("species"),
            'alive': dict_result.get("alive"),
            'note': dict_result.get("note"),
            'stranding': dict_result.get("stranding"),
            'self': live_link
        }

        return jsonify(response), 200

    # Delete a mammal based on created key from ID
    elif request.method == 'DELETE':
        # If mammal exists, delete mammal.
        if mammal != None:

            # If there are responder active on the stranding, remove each responder
            if mammal.get('stranding') != "":
                # Create key based on ID for mammal and get mammal
                stranding_key = client.key(constants.strandings, int(mammal.get('stranding')))
                stranding = client.get(key=stranding_key)

                mammal_list = []
                # Loop through each stranding in responder list and add all except entity being deleted
                for mammal in stranding.get('mammals'):
                    if mammal.get('id') != id:
                        mammal_list.append(mammal)

                # Update responder with stranding list that no longer has the stranding being deleted
                stranding.update({"mammals": mammal_list})
                client.put(stranding)

            client.delete(key)

            return '', 204

    # Update mammal information based on created key
    elif request.method == 'PATCH':
        content = request.get_json()

        # Check that fields provided are correct types
        error_message = field_constraint_check(content, True)
        if error_message != "":
            response = make_response(jsonify(Error=error_message))
            response.mimetype = "application/json"
            response.status_code = 400

            return response

        # If the mammal is not found, return 404
        if mammal == None:
            return jsonify(Error="No mammal with this mammal ID exists"), 404

        # Loop through fields that were updated in JSON and update on stranding
        for field in content:
            mammal.update({field: content[field]})

        client.put(mammal)

        live_link = request.base_url + str(mammal.get('id'))
        # Set response
        response = {
            'id': mammal.key.id,
            'species': mammal.get("species"),
            'alive': mammal.get("alive"),
            'note': mammal.get("note"),
            'stranding': mammal.get("stranding"),
            'self': live_link

        }

        response = make_response(jsonify(response))
        response.mimetype = "application/json"
        response.status_code = 200

        return response

    # Update mammal information based on created key
    elif request.method == 'PUT':
        content = request.get_json()

        # Check if all required attributes are passed to edit mammal
        if all([field in content.keys() for field in ['species', 'alive', 'note']]):
            # Check that fields provided are correct types
            error_message = field_constraint_check(content, True)
            if error_message != "":
                response = make_response(jsonify(Error=error_message))
                response.mimetype = "application/json"
                response.status_code = 400

                return response

            # If the mammal is not found, return 404
            if mammal == None:
                return jsonify(Error="No alive with this alive ID exists"), 404

            # Loop through fields that were updated in JSON and update on mammal
            for field in content:
                mammal.update({field: content[field]})

            client.put(mammal)

            live_link = request.base_url + str(mammal.get('id'))
            # Set response
            response = {
                'id': mammal.key.id,
                'species': mammal.get("species"),
                'alive': mammal.get("alive"),
                'note': mammal.get("note"),
                'stranding': mammal.get("stranding"),
                'self': live_link

            }

            response = make_response(jsonify(response))
            response.mimetype = "application/json"
            response.status_code = 200

            return response

        else:
            response = make_response(jsonify(Error="The request object is missing at least one of the required "
                                                   "attributes"))
            response.mimetype = "application/json"
            response.status_code = 400

            return response

    # Incorrect request found
    else:
        return jsonify(Error='Method not accepted')


# Add or remove a mammal from a stranding
@app.route('/strandings/<stranding_id>/mammals/<mammal_id>', methods={'PUT', 'DELETE'})
def add_remove_mammal_stranding(stranding_id, mammal_id):
    # Create key based on ID for stranding
    stranding_key = client.key(constants.strandings, int(stranding_id))
    # Create key based on ID for mammal
    mammal_key = client.key(constants.mammals, int(mammal_id))

    # Create stranding query
    query = client.query(kind=constants.strandings)
    query.key_filter(stranding_key, '=')

    # Return found result
    stranding_result = list(query.fetch())

    # Create mammal query
    query = client.query(kind=constants.mammals)
    query.key_filter(mammal_key, '=')

    # Return found result
    mammal_result = list(query.fetch())

    # If either a stranding or a mammal are not found, return error and 404
    if len(mammal_result) == 0 or len(stranding_result) == 0:
        return jsonify(Error="The specified stranding and/or mammal do not exist"), 404

    mammal = mammal_result[0]
    stranding = stranding_result[0]

    # Adds a mammal to a stranding
    if request.method == 'PUT':
        # Sets mammal with the stranding and adds stranding to the mammal
        # If the mammal is already assigned, return 403 and error
        if mammal.get("stranding") != "":
            return jsonify(Error="The mammal is already assigned to a stranding"), 403
        # If the mammal is not assigned already, set mammal to stranding 204
        else:
            # Set response for stranding and add to mammal
            mammal.update(stranding=stranding_id)

            # Set response for mammal and add to stranding
            mammal_obj = {
                'id': mammal_id,
                "species": mammal.get("species")
            }
            stranding['mammals'].append(mammal_obj)

            client.put(stranding)
            client.put(mammal)

            return '', 204

    # Removes a mammal from a stranding
    elif request.method == 'DELETE':
        # Removes mammal from the stranding and removes stranding from mammal
        # If the mammal is already assigned, return 403 and error
        if mammal.get("stranding") == "" or mammal.get("stranding") != stranding_id:
            return jsonify(Error="The mammal not assigned to a stranding or is assigned to a different stranding"), 403
        # If the mammal is assigned to the stranding, remove it from the stranding and return 204
        else:
            # Remove stranding from mammal and set to empty
            mammal.update(stranding="")

            idx = 0
            # Find and mammal from stranding
            for mammal in stranding.get("mammals"):
                if mammal.get("id") == mammal_id:
                    stranding.get("mammals").pop(idx)

                idx += 1

            client.put(stranding)
            client.put(mammal)

            return '', 204

# Get all users.
@app.route('/users', methods={'GET'})
def users_get():
    # Get all users and output
    if request.method == 'GET':
        query = client.query(kind=constants.users)
        results = list(query.fetch())

        result_list = []
        for e in results:
            dict_result = dict(e)

            entity = {
                'id': e.key.id,
                'username': dict_result.get("username"),
                'first_name': dict_result.get("first_name"),
                'last_name': dict_result.get("last_name"),
                'stranding': dict_result.get("stranding"),
            }

            result_list.append(entity)
        return jsonify(result_list), 200

    # Incorrect request found
    else:
        response = make_response(jsonify(Error="Method not found"))
        response.mimetype = "application/json"
        response.status_code = 404

        return response





# Check that JWT is valid and if not, return None, otherwise return sub value
def validate_authorization_page(req, jwt):
    # If authorization does not exist, throw 401
    if id_token == None:
        return None

    try:
        # Verify that JWT is valid
        id_info = id_token.verify_oauth2_token(jwt, req, CLIENT_ID)
    except:
        # If invalid, set to None
        id_info = None

    if id_info == None:
        return None
    else:
        return id_info['sub']

# Add user to datastore if does not exist already
def add_user(sub, first_name, last_name):
    # Create a mammal entity with given values
    new_user = datastore.entity.Entity(key=client.key(constants.users))
    new_user.update({"username": sub, "first_name": first_name, "last_name": last_name})

    # Send created mammal to datastore
    client.put(new_user)

# Check if user exists in datastore. Return None if not found. Otherwise, return user.
def user_exists(sub):
    query = client.query(kind=constants.users)
    query.add_filter('username', '=', sub)

    results = list(query.fetch())

    if len(results) == 0:
        return None

    return results


@app.route("/")
def welcome():
    # If there are no credentials, set URL to route to authorization for OAuth2
    if 'credentials' not in flask.session.keys():
        flask.session['state'] = str(uuid.uuid4())

        authorization_url = ('https://accounts.google.com/o/oauth2/v2/auth?response_type=code'
                             '&client_id={}&redirect_uri={}&scope={}&state={}').format(CLIENT_ID, REDIRECT_URI, SCOPE,
                                                                                       flask.session['state'])
    # If there are expired credentials, set URL to route to authorization for OAuth2 and remove old credentials
    elif datetime.now() > flask.session['time_expires']:
        flask.session['state'] = str(uuid.uuid4())
        flask.session.pop('credentials')
        flask.session.modified = True

        authorization_url = ('https://accounts.google.com/o/oauth2/v2/auth?response_type=code'
                             '&client_id={}&redirect_uri={}&scope={}&state={}').format(CLIENT_ID, REDIRECT_URI, SCOPE,
                                                                                       flask.session['state'])
    # Unexpired credentials exist, send to page with current credentials
    else:
        authorization_url = REDIRECT_URI

    try:
        return flask.render_template("welcome.html", value=authorization_url)
    except Exception as e:
        return str(e)


@app.route("/user_info")
def user_info():
    req = google_req.Request()
    credentials = None

    # Check if there are unexpired credentials present
    if 'credentials' in flask.session.keys():
        if datetime.now() < flask.session['time_expires']:
            credentials = flask.session['credentials']

        # If there are credentials but they expired, redirect to main page
        else:
            return flask.redirect("/")

    # If code exists, then request token for People API
    elif 'code' in flask.request.args:
        # Verify that state returned matches state sent
        state = flask.session['state']
        flask.session.modified = True

        state_returned = flask.request.args.get('state')
        if state_returned == state:
            auth_code = flask.request.args.get('code')
            data = {'code': auth_code,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'grant_type': 'authorization_code'}

            # Perform POST request
            request = requests.post('https://www.googleapis.com/oauth2/v4/token', data=data)

            # Set response to credentials in session
            flask.session['credentials'] = json.loads(request.text)
            flask.session['time_expires'] = datetime.now() + timedelta(
                seconds=flask.session['credentials']['expires_in'])
            flask.session.modified = True

            credentials = flask.session['credentials']

        # If state does not match, display error
        else:
            return flask.render_template("state_error.html", state_request=state_returned, state_session=state)

    # If there are no credentials, redirect to main page
    elif 'credentials' not in flask.session:
        return flask.redirect("/")

    headers = {'Authorization': 'Bearer {}'.format(credentials['access_token'])}
    req_uri = 'https://people.googleapis.com/v1/people/me?personFields=names,emailAddresses,phoneNumbers,organizations'
    people_response = requests.get(req_uri, headers=headers)

    json_people = people_response.json()

    person = json_people['names'][0]

    # If given name exists, set first_name
    if "givenName" in person.keys():
        first_name = person['givenName']
    else:
        first_name = ""

    # If last name exists, set last_name
    if "familyName" in person.keys():
        last_name = person['familyName']
    else:
        last_name = ""

    # Get the id_token
    id_token = credentials['id_token']

    flask.session['sub'] = validate_authorization_page(req, id_token)

    user = user_exists(flask.session.get('sub'))
    # Check if user exists already, if not add to datastore
    if user == None:
        # Add new user to datastore
        add_user(flask.session['sub'], first_name, last_name)

    try:
        return flask.render_template("user_info.html", f_name=first_name, l_name=last_name, state=flask.session['state'],
                                     id_token=id_token, sub=flask.session['sub'])
    except Exception as e:
        return str(e)


if __name__ == '__main__':
    app.run(port=8080)
