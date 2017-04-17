import json
import urllib.request
from urllib.error import URLError

import codecs
from app import db
from app.models.antenna import Antenna
from app.models.carrier import Carrier
from app.models.gsm_signal import GsmSignal
from app.models.gsm_count import GsmCount
from app.models.ranking import Ranking
from app.models.report import Report
from config import AppTokens
from config import ServerSettings
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.importation import reportLogger

urls = ServerSettings.urls
SERVER_BASE_URL = urls["server_url"]
ANTENNA_URL = urls["antenna_url"]
REPORT_URL = urls["report_url"]
RANKING_URL = urls["ranking_url"]
NETWORK_URL = urls["network_url"]
SIGNAL_URL = urls["signal_url"]
reader = codecs.getreader("utf-8")
token = AppTokens.tokens["server"]
header = {"Authorization": "token " + token}

# Handles the general report importation (Named general_report_month_year)
def report_import(year, month):
    reportLogger.info("Importing general report for {}/{}".format(month, year))
    url = SERVER_BASE_URL + "/" + REPORT_URL + "/" + str(year) + "/" + str(month) + "/general_report_{}_{}.json".format(month,year)
    request = urllib.request.Request(url, headers={"Authorization": "token " + token})
    carriers = Carrier.query.all()
    carrierIds = [c.id for c in carriers]

    try:
        response = urllib.request.urlopen(request)
        data = json.load(reader(response))

        # For each kind of report
        for report_type, element in data.items():

            if type(element) == dict:

                for carrier, quantity in element.items():

                    if carrier.isdigit():
                        carrier_id = int(carrier)
                    else:
                        continue

                    # Ignoring the carriers not listed
                    if carrier_id not in carrierIds:
                        continue

                    db.session.add(Report(year, month, report_type, carrier_id, quantity))
                    db.session.commit()

            else:
                carrier_id = 0
                db.session.add(Report(year, month, report_type, carrier_id, element))
                db.session.commit()
        reportLogger.info("Finished general report import for {}/{}".format(month, year))

    except URLError:
        reportLogger.error("Couldn't reach url {}".format(url))

    except ValueError:
        reportLogger.error("Couldn't reach url {}".format(url))

# Handles the ranking import reports
def ranking_import(year, month):
    reportLogger.info("Importing application ranking report for {}/{}".format(month, year))
    url = SERVER_BASE_URL + "/" + RANKING_URL + "/" + str(year) + "/" + str(month) + "/apps_report_{}_{}.json".format(month, year)
    print(url)
    request = urllib.request.Request(url, headers={"Authorization": "token " + token})
    carriers = Carrier.query.all()
    carrierIds = [c.id for c in carriers]

    try:
        response = urllib.request.urlopen(request)
        data = json.load(reader(response))

        for carrier, dict in data.items():

            if carrier == 'ALL_CARRIERS':
                carrier_id = 0
            else:
                carrier_id = int(carrier)

            if carrier_id not in carrierIds:
                continue

            for traffic_type, dict in dict.items():

                for transfer_type, rank in dict.items():

                    for ranking_number in sorted(rank.keys()):

                        ranking_info = rank[ranking_number]

                        db.session.add(Ranking(year=year, month=month, carrier_id=carrier_id,
                                               traffic_type=traffic_type.lower(),
                                               transfer_type=transfer_type.lower(),
                                               ranking_number=int(ranking_number),
                                               app_name=ranking_info["app_name"],
                                               bytes_per_user=ranking_info["bytes_per_user"],
                                               total_bytes=ranking_info["total_bytes"],
                                               total_devices=ranking_info["total_devices"]))
                        db.session.commit()

        reportLogger.error("Finished application ranking report import for {}/{}".format(month, year))
    except URLError:
        reportLogger.error("Couldn't reach url {}".format(url))

    except ValueError:
        reportLogger.error("Couldn't reach url {}".format(url))

# Handles the signal reports (Named signal_report_month_year)
def gsm_signal_import(year, month):
    reportLogger.info("Importing signal report for {}/{}".format(month, year))
    url = SERVER_BASE_URL + "/" + SIGNAL_URL + "/" + str(year) + "/" + str(month) + "/signal_report_{}_{}.json".format(month, year)
    print(url)
    request = urllib.request.Request(url, headers={"Authorization": "token " + token})
    carriers = Carrier.query.all()
    carrierIds = [c.id for c in carriers]

    try:
        response = urllib.request.urlopen(request)
        signals = json.load(reader(response))

        for signal in signals:
            antenna_id = signal["antenna_id"]
            carrier_id = signal["carrier_id"]
            quantity = signal["observations"]
            signal_mean = signal["signal_mean"]
            antenna = Antenna.query.get(signal["antenna_id"])

            # We ignore the carriers that are not in our database
            if carrier_id not in carrierIds:
                continue

            if not antenna:
                try:
                    ans = get_antenna(antenna_id)
                    if ans == 'Antenna with no lat or lon' or ans is None:
                        continue

                except DifferentIdException:
                    continue

            db.session.add(GsmSignal(year=year, month=month, antenna_id=antenna_id, carrier_id=carrier_id, signal=signal_mean, quantity=quantity))

            try:
                db.session.commit()

            except IntegrityError:
                db.session.rollback()
                signal = GsmSignal.query.filter_by(year=year, month=month, carrier_id=carrier_id, antenna_id=antenna_id).first()
                signal.quantity = quantity
                signal.signal = signal_mean
                db.session.commit()
        reportLogger.info("Finished signal report import for {}/{}".format(month, year))
    except URLError:
        reportLogger.error("Couldn't reach url {}".format(url))

    except ValueError:
        reportLogger.error("Couldn't reach url {}".format(url))


def gsm_count_import(year, month):
    reportLogger.info("Importing network report for {}/{}".format(month, year))
    url = SERVER_BASE_URL + "/" + NETWORK_URL + "/" + str(year) + "/" + str(month) + "/network_report_{}_{}.json".format(month,year)
    request = urllib.request.Request(url, headers={"Authorization": "token " + token})
    carriers = Carrier.query.all()
    carrierIds = [c.id for c in carriers]
    try:
        response = urllib.request.urlopen(request)
        counts = json.load(reader(response))
        for count in counts:
            antenna_id = count["antenna_id"]
            carrier_id = count["carrier_id"]
            quantity = count["size"]
            network_type = count["network_type"]
            antenna = Antenna.query.get(count["antenna_id"])

            if not carrier_id in carrierIds: # If carrier not in known carriers, we ignore it
                continue

            if not antenna:
                try:
                    ans = get_antenna(antenna_id)
                    if ans == 'Antenna with no lat or lon' or ans is None:
                        continue
                except DifferentIdException:
                    continue

            db.session.add(GsmCount(year=year, month=month, antenna_id=antenna_id, network_type=network_type,
                                    carrier_id=carrier_id, quantity=quantity))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                count = GsmCount.query.filter_by(year=year, month=month, carrier_id=carrier_id,
                                                  antenna_id=antenna_id, network_type=network_type).first()
                count.quantity = quantity
                db.session.commit()

        reportLogger.info("Finished network report import for {}/{}".format(month, year))
    except URLError:
        reportLogger.error("Couldn't reach url {}".format(url))

    except ValueError:
        reportLogger.error("Couldn't reach url {}".format(url))

# Gets the antenna if it is not inside our database
def get_antenna(id):
    reportLogger.info("Requesting antenna {} from database".format(id))
    url = SERVER_BASE_URL + "/" + ANTENNA_URL + "/" + str(id)
    request = urllib.request.Request(url, headers={"Authorization": "token " + token})
    try:
        response = urllib.request.urlopen(request)
        data = json.load(reader(response))
#        print(data)
        carrier_id = data["carrier_id"]
        cid = data["cid"]
        lac = data["lac"]
        lat = data["lat"]
        lon = data["lon"]

        # We add just the antennas that have known lat and lon
        if lat is None or lon is None:
            return 'Antenna with no lat or lon'

        db.session.add(Antenna(id=id, cid=cid, lac=lac, lat=lat, lon=lon, carrier_id=carrier_id))

        try:
            db.session.commit()
        except IntegrityError:
            try:
                db.session.rollback()
                antenna = Antenna.query.filter_by(id=id).first()
                antenna.lat = lat
                antenna.lon = lon
                db.session.commit()
            except:
                raise DifferentIdException()

    except ValueError:
        reportLogger.error("Couldn't reach url {}".format(url))
    except URLError:
        reportLogger.error("Couldn't reach url {}".format(url))

def antennas_import():
    id = db.session.query(func.max(Antenna.id))[0][0] + 1
    while True:
        try:
            get_antenna(id)
        except URLError:
            break
        id += 1


def refresh_materialized_views():
    reportLogger.info("Refreshing materialized views")
    try:
        sql = 'REFRESH MATERIALIZED VIEW gsm_count_by_carrier'
        db.engine.execute(sql)
        sql = 'REFRESH MATERIALIZED VIEW gsm_signal_statistic_by_carrier'
        db.engine.execute(sql)
    except Exception:
        reportLogger.error("Couldn't refresh materialized views")
    reportLogger.info("Finished refreshing materialized views")


def refresh_antennas_json():
    reportLogger.info("Refreshing antennas json")
    from app.models.network_type import NetworkType
    from app.models.gsm_count import GsmCount
    from app.models.carrier import Carrier
    from sqlalchemy import func
    try:
        carriers = Carrier.query.all()
        carriers = ['0'] + [str(c.id) for c in carriers]
        for carrier in carriers:
            reportLogger.info("Refreshing antennas json for carrier {}".format(carrier))
            if carrier == '0':
                query = GsmCount.query
            else:
                query = GsmCount.query.filter(GsmCount.carrier_id == carrier)
            result = query.join(NetworkType).join(Antenna).join(Carrier, Carrier.id == Antenna.carrier_id).with_entities(
                func.sum(GsmCount.quantity).label('c'),
                GsmCount.antenna_id, NetworkType.type, Carrier.name, Antenna.lat, Antenna.lon
            ).group_by(GsmCount.antenna_id, NetworkType.type, Carrier.name, Antenna.lat, Antenna.lon).all()

            antennas_data = {}
            atennas_count = 0
            for row in result:
                antenna_id = row.antenna_id
                quantity = row.c
                network_type = row.type
                carrier_name = row.name
                lat = row.lat
                lon = row.lon
                if antenna_id not in antennas_data:
                    antennas_data[antenna_id] = {'lat': lat,
                                                 'lon': lon,
                                                 'carrier': carrier_name,
                                                 '2G': 0,
                                                 '3G': 0,
                                                 '4G': 0,
                                                 'Otras': 0,
                                                 'Total': 0}

                    atennas_count += 1
                antennas_data[antenna_id][network_type] = quantity
                antennas_data[antenna_id]['Total'] += quantity
            antennas_info = {'antennasData': antennas_data,
                            'totalAntennas': atennas_count}
            with open("app/static/json/gsm_count/"+carrier+".json", "w") as jsonfile:
                    json.dump(antennas_info, jsonfile)
            reportLogger.info("Finished refreshing antennas json for carrier {}".format(carrier))
    except Exception:
        reportLogger.error("Couldn't refresh antennas json")


def import_all(year, month):
    report_import(year, month)
    ranking_import(year, month)
    gsm_signal_import(year, month)
    gsm_count_import(year, month)

    refresh_materialized_views()
    refresh_antennas_json()


class DifferentIdException(Exception):
    pass
