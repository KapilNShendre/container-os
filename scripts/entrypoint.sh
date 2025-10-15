#!/bin/sh
set -e

# Create /dev/fuse if it doesn't exist
if [ ! -e /dev/fuse ]; then
    mknod /dev/fuse c 10 229
    chmod 666 /dev/fuse
fi

if command -v sshd >/dev/null 2>&1; then
    mkdir -p /run/sshd /var/run/sshd
    ssh-keygen -A
    
    if [ -d /home/miget/.ssh ]; then
        chown -R miget:miget /home/miget/.ssh
        chmod 700 /home/miget/.ssh
        if [ -f /home/miget/.ssh/authorized_keys ]; then
            chmod 600 /home/miget/.ssh/authorized_keys
        fi
    fi
fi

if command -v crond >/dev/null 2>&1; then
    mkdir -p /var/spool/cron/crontabs
fi

if command -v podman >/dev/null 2>&1; then
    mkdir -p /var/run/podman /run/podman
    
    # Configure subuid/subgid for rootless podman
    if ! grep -q "^miget:" /etc/subuid 2>/dev/null; then
        echo "miget:100000:65536" >> /etc/subuid
    fi
    if ! grep -q "^miget:" /etc/subgid 2>/dev/null; then
        echo "miget:100000:65536" >> /etc/subgid
    fi
    
    podman system migrate >/dev/null 2>&1 || true
fi

# Detect supervisord config location (Alpine vs Debian/Ubuntu)
if [ -f /etc/supervisord.conf ]; then
    SUPERVISOR_CONF=/etc/supervisord.conf
elif [ -f /etc/supervisor/supervisord.conf ]; then
    SUPERVISOR_CONF=/etc/supervisor/supervisord.conf
else
    echo "Error: supervisord.conf not found"
    exit 1
fi

echo "Starting supervisord..."
exec /usr/bin/supervisord -c "$SUPERVISOR_CONF"
