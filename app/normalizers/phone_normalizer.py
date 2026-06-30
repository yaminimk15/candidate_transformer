import phonenumbers


class PhoneNormalizer:

    @staticmethod
    def normalize(phone, region: str = "IN"):

        try:
            parsed = phonenumbers.parse(phone, region)

            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed,
                    phonenumbers.PhoneNumberFormat.E164
                )

        except Exception:
            pass

        return None