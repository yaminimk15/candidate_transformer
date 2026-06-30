from app.models.candidate import Candidate

candidate = Candidate(
    full_name="Aakash K",
    emails=["aakash@gmail.com"]
)

print(candidate.model_dump())