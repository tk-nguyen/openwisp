from flask_wtf import FlaskForm
from wtforms.fields.simple import SubmitField
from wtforms.validators import InputRequired, MacAddress
from wtforms import StringField


class CreateDeviceForm(FlaskForm):
    name = StringField(
        "Name *", validators=[InputRequired("Please enter a valid name!")]
    )
    organization = StringField("Organization")
    mac_address = StringField(
        "MAC address *",
        validators=[InputRequired("Please enter a valid MAC address!"), MacAddress()],
    )


class RunCommandForm(FlaskForm):
    command = StringField(
        "Command", validators=[InputRequired("Please enter a valid command!")]
    )
