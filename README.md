https://github.com/mkhorasani/Streamlit-Authenticator?tab=readme-ov-file#4-setup
https://ploomber.io/blog/streamlit-password/

# Datalings


--> check out [**OnTheScales @ streamlit.app**](https://datalings.streamlit.app/) to see it in action!

## Features


## Installation

Clone this repository

```bash
git clone https://github.com/azabicki/OnTheScales
```

### virtual environment

_Datalings_ is written in `Python 3.12.8`.

#### venv
Install a virtual environment according to your OS:

##### MacOS & Linux

```bash
brew install mysql@8.4 mysql-client pkg-config
```

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

##### Windows

```bash
py -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Conda

If you are using _*conda_, an environment.yml file is provided, which also installs the required python version `3.12.8`:

```bash
conda env create -f environment.yml
conda activate Datalings
```

## Usage

To start the app, run the following command:

```bash
streamlit run datalings.py
```

The app will be available at http://localhost:8501.

Using _OnTheScales_ is straightforward. Simply select a user profile from the dropdown menu, and start tracking your body composition. You can also create multiple user profiles to track different persons.

## Raspberry Pi

_OnTheScales_ can also be run on a Raspberry Pi, I did it on an older Raspberry Pi 3B+. The following steps are required to install and run _OnTheScales_ on a Raspberry Pi:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### autostart

There is also script to start _OnTheScales_ in the `misc/RaspPi` folder. It will start the app in the background and automatically start when the Raspberry Pi boots.

In the following commands, first edit the `path` to the _OnTheScales_ folder, and then run these in your bash console:

```bash
EDIT_THIS_PATH="/path/to/OnTheScales"

chmod +x $EDIT_THIS_PATH/misc/RaspPi/autorun_OnTheScales.sh

echo "# ----- autostart OnTheScales after boot -----" >> ~/.bashrc
echo "if [ \$(tty) == /dev/tty1 ]; then" >> ~/.bashrc
echo "    $EDIT_THIS_PATH/misc/RaspPi/autorun_OnTheScales.sh" >> ~/.bashrc
echo "fi" >> ~/.bashrc
```

## Data Privacy

This application runs entirely locally on your machine. All user data is stored in CSV files in the `data/` directory, ensuring complete control over your personal information.

## Contributing

Feel free to open issues or submit pull requests if you have suggestions for improvements.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.
