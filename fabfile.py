from fabric.api import *

env.hosts = ['gimmeservers.com']
env.key_filename = '/home/vagrant/.ssh/id_rsa'
env.user = 'root'

def deploy():
    run('mkdir -p /usr/local/share/wsgi')
    local('git archive --format=tar --prefix=gimmeservers/ HEAD | gzip >gimmeservers.tar.gz')
    put('gimmeservers.tar.gz', '/tmp/')
    with cd('/usr/local/share/wsgi'):
        run('tar xf /tmp/gimmeservers.tar.gz')
    with settings(warn_only=True):
        result = run('restart gimmeservers')
    if result.failed:
        run('start gimmeservers')
