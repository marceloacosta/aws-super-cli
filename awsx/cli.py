import typer

app = typer.Typer(help="AWS Super CLI – one-command resource visibility")

@app.command()
def ls(service: str):
    """
    Placeholder for the killer command:
    lists resources across accounts/regions.
    """
    typer.echo(f"Coming soon: listing {service}…")

if __name__ == "__main__":
    app() 