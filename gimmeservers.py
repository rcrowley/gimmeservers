from flask import Flask, Response, jsonify, render_template, request
import hashlib
import hmac
from libcloud.types import InvalidCredsError, Provider
from libcloud.providers import get_driver
import os
import socket
import struct

DEBUG = 'GIMMESERVERS_VIA' not in os.environ

SECRET = 'This is my secret.  There are many like it but this one is mine.'

class Dummy(object):
    """
    Use this class in places where an object with an id attribute is needed
    but getting a real one would involve an extra round-trip to Rackspace.
    """
    def __init__(self, id=None):
        self.id = id

def _conn(username, api_key):
    pass

IMAGES = [(69, 'Ubuntu 10.10 (maverick)'),
          (49, 'Ubuntu 10.04 LTS (lucid)'),
          (4, 'Debian 5.0 (lenny)'),
          (51, 'CentOS 5.5'),
          (71, 'Fedora 14')]

SIZES = [(1, '256 server'),
         (2, '512 server'),
         (3, '1GB server'),
         (4, '2GB server'),
         (5, '4GB server'),
         (6, '8GB server'),
         (7, '15.5GB server')]

def _image(conn, image_id):
    image_id = int(image_id)
    images = conn.list_images()
    for image in images:
        if int(image.id) == image_id:
            return image
    raise KeyError

def _size(conn, size_id):
    size_id = int(size_id)
    sizes = conn.list_sizes()
    for size in sizes:
        if int(size.id) == size_id:
            return size
    raise KeyError

def _mac(provider, id, ip):
    return hmac.new(SECRET,
                    '{0}-{1}-{2}'.format(provider, id, ip),
                    hashlib.sha1).hexdigest()

def _url(provider, id, ip):
    ip = struct.unpack('L', socket.inet_aton(ip))[0]
    return '{0}://{1}/{2}-{3}-{4}-{5}'.format('http',
                                              '33.33.33.33:5000',
                                              provider,
                                              id,
                                              ip,
                                              _mac(provider, id, ip))

app = Flask(__name__)
app.config.from_object(__name__)

def _api_error(status_code, error):
    response = jsonify(error=error)
    response.status_code = status_code
    return response

@app.route('/api/create', methods=['POST'])
def api_create():

    if '' == request.form['name']:
        return _api_error(400, 'Invalid name.')
    if 'rax' != request.form['provider']:
        return _api_error(400, 'Provider must be "rax".')

    Driver = get_driver(Provider.RACKSPACE) 
    try:
        conn = Driver(request.form['username'], request.form['api_key']) 
    except InvalidCredsError:
        return _api_error(401, 'Invalid credentials.')

    # TODO What exceptions can this throw?
    node = conn.create_node(name=request.form['name'],
                            image=Dummy(request.form['image']),
                            size=Dummy(request.form['size']))

    return jsonify(ip=node.public_ip[0],
                   password=node.extra['password'],
                   provider=request.form['provider'],
                   id=node.id,
                   url=_url(request.form['provider'],
                            node.id,
                            node.public_ip[0]))

@app.route('/api/destroy', methods=['POST'])
def api_destroy():

    if 'rax' != request.form['provider']:
        return _api_error(400, 'Provider must be "rax".')

    Driver = get_driver(Provider.RACKSPACE) 
    try:
        conn = Driver(request.form['username'], request.form['api_key']) 
    except InvalidCredsError:
        return _api_error(401, 'Invalid credentials.')

    try:
        conn.destroy_node(Dummy(request.form['id']))
    except Exception as e:
        if '404' == str(e)[0:3]:
            return _api_error(404, 'Invalid id.')
        raise e

    return Response(status=204)

@app.route('/', methods=['GET'])
def page_create():
    return render_template('create.html',
                           provider='rax',
                           images=IMAGES,
                           sizes=SIZES)

@app.route('/<provider>-<id>-<ip>-<mac>', methods=['GET'])
def page_destroy(provider, id, ip, mac):
    if _mac(provider, id, ip) != mac:
        return render_template('404.html'), 404
    ip = socket.inet_ntoa(struct.pack('L', long(ip)))
    return render_template('destroy.html',
                           provider=provider,
                           id=id,
                           ip=ip)

if '__main__' == __name__:
    app.run(host='0.0.0.0')
