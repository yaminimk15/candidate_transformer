from app.extractors.resume_extractor import ResumeExtractor
from app.extractors.resume_parser import ResumeParser

extractor = ResumeExtractor()
parser = ResumeParser()

text = extractor.extract("data/sample_resume.pdf")

candidate = parser.parse(text)

print(candidate)