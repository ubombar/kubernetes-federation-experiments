#/usr/bin/sh


# Configure the repo
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y

# Install
sudo apt install python3.10
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
python3.10 -m pip install --upgrade pip

# python3.10 --version
# python3.10 -m pip --version

# Install the requirements
python3.10 -m pip install -r requirements.txt

