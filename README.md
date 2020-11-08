# scripts

collection of scripts to ease the renting process, and to maintaine the organizational stuff

| File                              | Description                                                                                                                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| mirror_screen.py                  | Privacy friendly customer display - Show the first screen on the second screen only if the leih.lokal website is open                                                                  |
| leihlokal.py                      | Parse the local Excel database and perform checks: Which items are overdue (send reminders) - which customers should be deleted due to inactivity - is everything synced?              |
| statistics.py                     | Parse the local Excel database and create statistics based on that                                                                                                                     |
| sync_products.py                  | Add the SKU (item number) to all items on WordPress/WooCommerce, so that we can search via SKU on the WordPress website as well (which is usually a premium feature that we didnt buy) |
| create_presentation_for_window.py | Create the ppt for the showcase window that cycles through all items that we have on offer                                                                                             |

# Setup Raspberry

    sudo apt-get upgrade && sudo apt-get upgrade
    git clone https://github.com/apache/couchdb.git
    git clone https://github.com/leih-lokal/LeihLokalVerwaltung.git

## Install Couchdb

https://docs.couchdb.org/en/stable/install/unix.html#

### Install dependencies

    sudo apt-get install -y gnupg ca-certificates
    echo "deb https://apache.bintray.com/couchdb-deb buster main" | sudo tee /etc/apt/sources.list.d/couchdb.list
    curl -sL https://deb.nodesource.com/setup_10.x | sudo bash -
    sudo apt-get install -y nodejs

### Build from source

    cd couchdb
    git checkout tags/3.1.1
    ./configure --disable-docs
    make release

### Copy binaries to home folder and delete source

    cd ~ && cp -r ./couchdb/rel/couchdb ./couchdb-release
    rm -r couchdb

### Copy config file

    cp LeihLokalVerwaltung/.devcontainer/couchdb/local.ini couchdb-release/etc/local.ini

### Autostart using systemd

Create a file /etc/systemd/system/couchdb.service:

    [Unit]
    Description=Couchdb service
    After=network.target

    [Service]
    Type=simple
    User=pi
    ExecStart=/home/pi/couchdb-release/bin/couchdb -o /dev/stdout -e /dev/stderr
    Restart=always

    [Install]
    WantedBy=multi-user.target

Enable & Start Service:

    sudo systemctl daemon-reload
    sudo systemctl enable couchdb.service
    sudo systemctl start couchdb.service
