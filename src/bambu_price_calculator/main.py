"""Entrypoint voor PandaPrice."""

from bambu_price_calculator.app import App


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()
