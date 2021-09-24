Youtube Content: https://youtu.be/GVcqozy_q6M

Subscribe to my Youtube channel: http://youtube.com/c/MikeMiner316?sub_confirmation=1

### Installation below is by running 
pip3 install -r requirements.txt


### NOTE: if TA-Lib got error, install this below for macOS
1) brew install ta-lib
2) xcode-select --install
3) pip3 install TA-Lib


#### Ubuntu - ARM (e.g. Odroid N2) Installation

wget -c http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz

tar xvzf ta-lib-0.4.0-src.tar.gz

cd ta-lib

wget 'http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.guess;hb=HEAD' -O config.guess

wget 'http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.sub;hb=HEAD' -O config.sub

make

sudo make install

cd .. && pip3 install -r requirements.txt




