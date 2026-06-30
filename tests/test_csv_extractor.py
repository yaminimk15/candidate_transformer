from app.extractors.csv_extractor import CSVExtractor


extractor = CSVExtractor()

data = extractor.extract("data/recruiter.csv")

print(data)