from app.extractors.resume_extractor import ResumeExtractor

extractor = ResumeExtractor()

text = extractor.extract("data/sample_resume.pdf")

print(text)