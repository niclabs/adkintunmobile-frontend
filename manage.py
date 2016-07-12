from flask_migrate import Migrate, MigrateCommand

from flask import g
from flask_script import Manager

from app import app, db

migrate = Migrate(app, db)
manager = Manager(app)

from manage_commands import PopulateAntennas, Populate

manager.add_command('db', MigrateCommand)
manager.add_command('populate', Populate())
manager.add_command('populate_antennas', PopulateAntennas())

if __name__ == '__main__':
    manager.run()
