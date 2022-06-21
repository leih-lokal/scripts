# scripts

collection of scripts to ease the renting process, and to maintaine the organizational stuff

| File                              | Description                                                                                                                                                                                          |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| mirror_screen.py                  | Privacy friendly customer display - Show the first screen on the second screen only if the leih.lokal website is open                                                                                |
| leihlokal.py                      | a Python interface to our couch-db. You can use this to automatically filter e.g. for due reminders                                                                                                  |
| website.py                        | some classes and functions to interface with the wordpress data.                                                                                                                                     |
| statistics.py                     | Parse the local Excel database and create statistics based on that                                                                                                                                   |
| sync_products.py                  | Add the SKU (item number) to all items on WordPress/WooCommerce, so that we can search via SKU on the WordPress website as well (which is usually a premium feature that we didnt buy)               |
| create_presentation_for_window.py | Create the ppt for the showcase window that cycles through all items that we have on offer                                                                                                           |
| create_clickcollect_overview.py   | Make a printable overview of all click&collect appointments for a specific day                                                                                                                       |
| daily_tasks.py                    | Send reminders for items that are returned too late. Check that the website and the database are in sync. Check which customer data need to be removed after 2 years of inactivity of that customer. |
| /ReturnReminderManager/           | script that is run via github-actions / cronjob to automatically send reminders the day before due return date                                                                                       |
| /WPAppointmentManager/            | script to auto-accept appointments made through our click&collect system                                                                                                                             |
|                                   |                                                                                                                                                                                                      |

# Setup Raspberry

    sudo apt-get upgrade && sudo apt-get upgrade
    git clone https://github.com/apache/couchdb.git
    git clone https://github.com/leih-lokal/leih.lokal.git
    git clone https://github.com/leih-lokal/LeihLokalVerwaltung.git

## Install Slideshow

### Create Slideshow PDF

Create the slideshow on your machine:

    cd leih.lokal
    pip install -r create_presentation_requirements.txt
    python create_presentation_for_window.py

Open `raspberry-pi-fenster.pptx` and export it as pdf. Then copy the pdf to `/home/pi/Schreibtisch/raspberry-pi-fenster.pdf` on the raspberry.

### Autostart

On Raspberry

    sudo apt-get install -y okular
    cd leih.lokal
    sudo chmod +x start-slideshow.sh

Add the following line to the file `/etc/xdg/lxsession/LXDE-pi/autostart`

    /home/pi/leih.lokal/start-slideshow.sh

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

## Setup automatic backup to Excel

Install dependencies

    cd ~/LeihLokalVerwaltung/ExcelCouchDbSync
    pip3 install -r requirements.txt
    chmod +x backup_to_excel.sh

Schedule cronjob (crontab -e)

    */30 10-20 * * 1,4-6 /home/pi/LeihLokalVerwaltung/ExcelCouchDbSync/backup_to_excel.sh >/dev/null 2>&1

## WordPress files for displaying custom changes

There are a couple of changes made to some of the WordPress files that enable customization of how products get displayed individually, in the search and also in the overview of the catalog. There are many more changes made, but before the time we joined the leihlokal, and sometimes it can be a bit of a pain to track down in which file which change needs to be made

**Change color of  "ausgeliehen", "verfügbar"**

This is set in `wp-content/themes/JointsWP/assets/styles/styles.css`

```php
/* WOOCOMMERCE */

.stock.out-of-stock{
    font-size: medium;
    color: red;
}
.stock.in-stock{
    font-size: medium;
    color: green;
}
```

**Display Meta fields**

there are different functions in the `wp-content/themes/JointsWP/function.php` that inject them via action-hooks

**Products in search results**

Each item gets displayed via `wp-content/themes/JointsWP/parts/loop-archive-grid.php`, there are quite a few changes there that were adapted



**Custom status names**

You can customize the status displays for "available" and "onbackorder" in the `functions.php` in the hook `wcs_custom_get_availability`