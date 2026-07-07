import collect_gfs
import database_connection
import util_gfs
import date_config

import index_calculation.calculate_tci
import index_calculation.calculate_hci
import index_calculation.calculate_utci


if __name__ == "__main__":
    collect_gfs.main()
    
    index_calculation.calculate_tci.main()
    index_calculation.calculate_hci.main()
    index_calculation.calculate_utci.main()
