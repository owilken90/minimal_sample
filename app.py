import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import boto3
from botocore.exceptions import ClientError
import os




########################################################################
#                       SEND MAIL                                      #
########################################################################


def send_mail(sender, recipients, message, subject):

    print("preparing mail to {}".format(recipients))

    message = message.replace("\n", "<br>")

    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    SENDER = "CoordinatorGPT <"+ sender +">"

    # Specify a configuration set. If you do not want to use a configuration
    # set, comment the following variable, and the
    # ConfigurationSetName=CONFIGURATION_SET argument below.
    #CONFIGURATION_SET = "ConfigSet"

    # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    AWS_REGION = "eu-west-1"


    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = message

    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
    <p id="do_not_delete_this"></p>
    <p>""" + message + \
    """</p>
    </body>
    </html>
    """

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)


    #Provide the contents of the email.
    response = client.send_email(
        Destination={
            'ToAddresses': recipients,
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': BODY_HTML,
                },
                'Text': {
                    'Charset': CHARSET,
                    'Data': BODY_TEXT,
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': subject,
            },
        },
        Source=SENDER,
        # If you are not using a configuration set, comment or delete the
        # following line
        #ConfigurationSetName=CONFIGURATION_SET,
    )

    return response





########################################################################
#                       Dashboard                                      #
########################################################################



# Initialize the Dash app and set the theme to a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout of the app
app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.H1("Dash", className="text-center"),
                width=12
            )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Button("Click Me", id="example-button", color="primary", className="mr-2"),
                width={"size": 6, "offset": 3},
                className="text-center"
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="output-div", className="mt-4"),
                width=12
            )
        )
    ],
    fluid=True
)

# Callback to update the output div when the button is clicked
@app.callback(
    Output("output-div", "children"),
    [Input("example-button", "n_clicks")]
)
def send_mail_callback(n_clicks):
    if n_clicks is None:
        return "No mail send yet."
    else:
        sender = f"mail{n_clicks}@coordinatorgpt.com"
        recipients = ["o.wilken90@gmail.com", "Jonas.Wilken@proton.me"]
        message = f"Hi, this is mail number {n_clicks}"
        subject = f"Mail number {n_clicks}"
        send_mail(sender, recipients, message, subject)
        return f"Number of send mails: {n_clicks}"

# Run the app
if __name__ == "__main__":
    app.run_server(debug=False)
