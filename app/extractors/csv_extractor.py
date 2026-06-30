import pandas as pd


class CSVExtractor:

    def extract(self, file_path: str):

        df = pd.read_csv(file_path)

        records = df.to_dict(orient="records")

        return records