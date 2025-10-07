# Decoders for EOT and HOT telemetry


def xor(a, b):
    ret = ""
    for i in range(len(b)):
        if a[i] == b[i]:
            ret += "0"
        else:
            ret += "1"
    return ret


# function from geeks4geeks: https://www.geeksforgeeks.org/modulo-2-binary-division/
# adding [1:] to everything makes it work, idk why, credit to Eric Reuter for figuring that out
def mod2div(dividend, divisor):
    # Number of bits to be XORed at a time.
    pick = len(divisor)

    # Slicing the dividend to appropriate
    # length for particular step
    tmp = dividend[0:pick]

    while pick < len(dividend):

        if tmp[0] == "1":

            # replace the dividend by the result
            # of XOR and pull 1 bit down
            tmp = xor(divisor[1:], tmp[1:]) + dividend[pick]

        else:  # If leftmost bit is '0'
            # If the leftmost bit of the dividend (or the
            # part used in each step) is 0, the step cannot
            # use the regular divisor; we need to use an
            # all-0s divisor.
            tmp = xor(("0" * pick)[1:], tmp[1:]) + dividend[pick]

        # increment pick to move further
        pick += 1

    # For the last n bits, we have to carry it out
    # normally as increased value of pick will cause
    # Index Out of Bounds.
    if tmp[0] == "1":
        tmp = xor(divisor[1:], tmp[1:])
    else:
        tmp = xor(("0" * pick)[1:], tmp[1:])

    checkword = tmp
    return checkword


# This whole file is heavily inspired by PyEOT. Credit goes to Eric Reuter for the creation of it.
# The student team was given permission by Eric to utilize PyEOT for this project, this is our recreation of it.
class EOTDecoder:

    # for decoding EOT's, theres a lot that goes into it
    # first is the frame sync, which is determined before it hits this file
    # important thing to note: all multi-bit data fields are in little endian, meaning they need to be reversed

    def __init__(self):
        return

    # this function decodes an EOT signal into the information we need, and returns a dictionary with all the data.
    # if the EOT information is somehow not valid, it returns None.
    def decode_eot(self, data):
        # theres 56 bits that we care about, despite sending in 74 bits. The last 18 bits create the checksum
        # the first 11 is the frame sync, which is used to tell you that its an EOT signal
        # the next 2 are chaining bits. I'm not too sure what this means, but its there
        # the following 3 determine the message type
        # battery condition is 2 bits after, and has 4 states
        # unit address is 17 bits, and is unique to each EOT device
        # brake pipe pressure is 7 bits, and ranges from 0 to 125 psig
        # battery charge is also 7 bits, but uses the full range
        # single discretionary bit after this, the value and what it means depend on the EOT manufacturer, its mostly ignored
        # valve status is next, on or off
        # responding to HOT device bit, on or off
        # turbine status, on or off
        # whether the train is in motion, yes or no
        # marker light battery, this one is weird. 0 means it is either on or not being tracked, 1 means its weak
        # marker light status, on or off
        # the next 18 is the checksum, which is used to ensure that everything is valid.
        # theres a trailing bit after which is always a one.

        full_data = data[
            11:56
        ]  # removing the frame sync - this makes sense later i promise
        checksum = data[56:74]
        frame_sync = data[0:11]  # unneccesary but whatever
        filler_bits = data[
            11:12
        ]  # saving this even though its useless - its a filler bit so the memory allocation doesnt get funky
        battery_condition = data[13:15][
            ::-1
        ]  # first bit of real data, little endian means its reversed
        message_type = data[
            15:18
        ]  # techincally this one is reversed, but its only ever 000 or 111 so it doesnt matter
        unit_address = data[18:35][::-1]
        brake_pressure = data[35:42][::-1]
        battery_charge = data[42:49][::-1]
        discretionary_bit = data[
            49
        ]  # not sure whats put here, apparently it depends on the EOT manufacturer
        valve_status = data[50]  # 0 means its not working, 1 means its functional
        confirmation_indicator = data[51]  # are we talking to the HOT?
        turbine_status = data[52]
        in_motion = data[53]
        marker_light_battery = data[
            54
        ]  # this really should be 2 bits but im not gonna argue
        marker_light_status = data[55]
        trailing_bit = data[74]  # this should always be 1.

        # trailing bit should always be one.
        if trailing_bit != "1":
            return None

        """ 
        # check the validity of the eot bits
        # thanks Eric for the explanation of how this works, check out his DEFCON talk about this if you have the time
        # using the checker and the cipher, we should be able to recreate the checksum stored in the data
        # by getting the remainder of the reversed data divided by the "checker" and then performing an XOR on the cipher
        # we should get the checksum itself. If they are the same, then the data is valid.
        # this technique is known as Cyclic Redundancy Checking, heres a good article on it: https://www.geeksforgeeks.org/cyclic-redundancy-check-python/
        """
        checksum_checker = 0b1111001101000001111  # gotten from Eric's talk - its a BCH generator polynomial. Feel free to research it, it's pretty interesting.
        cipher = 0b101011011101110000  # also gotten from Eric's talk

        # first, reverse the data block and get the remainder of it divided by the checker
        reversed_data = full_data[::-1]

        # check that information is valid
        padded_data = reversed_data + (
            "0" * 18
        )  # use 19-1 bits because of bch polynomial stuff
        remainder = mod2div(
            padded_data, bin(checksum_checker)[2:]
        )  # perform modulo 2 division (a weird xor thing used in CRC)
        recreated_checksum = xor(remainder, bin(cipher)[2:])  # xor by the cipher
        # weird note: only the EOT does this xor cipher? the HOT doesnt, which imo is an interesting security difference,
        # my guess is its because the EOT sends way more information than the HOT
        
        # print(checksum)
        # print(recreated_checksum)
        # # print(bin(checkbit_checker)[2:])
        # # print(bin(cipher)[2:])
        # print(bin(int((full_data), 2))[2:])
        # print(reversed_data)
        # print(bin(zeroes)[2:])
        
        # set arm status
        return_arm_status = None
        if message_type == "111":
            if confirmation_indicator == "0":
                return_arm_status = "Arming"
            else:
                return_arm_status = "Armed"
        else:
            return_arm_status = "Unarmed"

        # set battery condition
        return_battery_condition = None
        battery_condition_key = {
            "11": "Good",
            "10": "Low",
            "01": "Very Low",
            "00": "Unknown",
        }

        data_to_return = {
            "unit_address": int(unit_address, 2),
            "arm_status": return_arm_status,
            "battery_condition": battery_condition_key[battery_condition],
            "battery_charge": (int(battery_charge, 2) / 127) * 100,
            "pressure": int(brake_pressure, 2),
            "turbine_status": turbine_status,
            "motion_status": in_motion,
            "marker_light": marker_light_status,
            "marker_battery": marker_light_battery,
            "hot_command": confirmation_indicator,
        }
        if recreated_checksum == checksum:
            return data_to_return
        return None

# Same as EOTDecoder, heavily inspired by Eric Reuter's PyEOT, recreated with permission from Eric
class HOTDecoder:

    def __init__(self):
        return

    def decode_hot(self, data):
        """
        # data is a string of binary data. time to do more funny business!
        # using the ES Protocol ICD Document as a reference, we know that
        # in theory, data sends up 456 binary bits. We only need about 64 of them i believe, as the rest is bit padding because of frequencies and whatnot.
        # again, all multi bit pieces of information is little endian, so we need to reverse it
        """
        full_data = data[24:88]
        main_information = data[24:54]
        unit_address = data[29:46][::-1]
        command = int(data[46:54][::-1], 2)
        checksum = data[54:87]
        parity = data[87]

        checksum_checker = 0b1110011011010111000010110011111011
        reversed_information = main_information[::-1]
        padded_data = reversed_information + (
            "0" * 33
        )  # same idea as padding by 18 in EOT
        created_checksum = mod2div(
            padded_data, bin(checksum_checker)[2:]
        )  # no cipher on HOT, not sure why but instead we use parity
        parity_valid = self.parity_check(full_data)
        if created_checksum == checksum and parity_valid:
            command_dict = {
                0b10101010: "Emergency message",
                0b01010101: "Status request",
            }
            data_to_return = {
                "unit address": int(unit_address, 2),
                "command": command_dict[command],
            }

            return data_to_return
        return None

    def parity_check(self, data):
        """
        The parity bit is used in an "Odd-Parity" function. That is,
        the parity bit is used to ensure that there is always an odd number
        of 1's in the data.
        If the number of 1's in the data stream modulo 2 == 1, it is odd, and therefore
        the data is valid, assuming the checksum matches.
        """
        num_ones = data.count("1")
        if (num_ones % 2) == 1:
            return True
        return False


# TODO: Add DPU, utilizing information from the patent (US Patent 4582280)
