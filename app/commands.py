# app/commands.py
import click
from flask.cli import with_appcontext
from . import db
from .models import User

@click.command("create-user")
@click.option("--email", prompt=True)
@click.option("--name", prompt=True)
@click.option("--role", default="staff", show_default=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_user(email, name, role, password):
    email = email.strip().lower()

    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo("User already exists.")
        return

    user = User(email=email, name=name, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    click.echo(f"Created user: {email} ({role})")
