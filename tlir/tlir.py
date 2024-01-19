def calc_tlir(mtlcr, speed_list, max_speed):
    if len(speed_list) == 0:
        return 0

    avg_speed = sum(speed_list) / len(speed_list)
    return round(mtlcr * (avg_speed / max_speed), 4)
