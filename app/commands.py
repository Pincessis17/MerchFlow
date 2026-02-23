# app/commands.py
import click
from flask.cli import with_appcontext
from . import db
from .models import Company, User

@click.command("create-user")
@click.option("--email", prompt=True)
@click.option("--name", prompt=True)
@click.option("--role", default="staff", show_default=True)
@click.option("--company-id", type=int, default=None, help="Existing company ID")
@click.option("--company-name", default=None, help="Create/find company by name")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_user(email, name, role, company_id, company_name, password):
    email = email.strip().lower()
    role = (role or "staff").strip().lower()

    company = None
    if company_id:
        company = Company.query.get(company_id)
    elif company_name:
        cname = company_name.strip()
        if cname:
            company = Company.query.filter_by(name=cname).first()
            if not company:
                company = Company(name=cname, email=email, status="active")
                db.session.add(company)
                db.session.flush()

    if not company:
        click.echo("A valid company is required. Use --company-id or --company-name.")
        return

    existing = User.query.filter_by(company_id=company.id, email=email).first()
    if existing:
        click.echo("User already exists.")
        return

    user = User(company_id=company.id, email=email, name=name, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    click.echo(f"Created user: {email} ({role}) in company {company.id}")
