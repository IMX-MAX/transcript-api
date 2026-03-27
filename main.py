import json
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

def main(context):
    """
    Appwrite Function entry point for fetching YouTube transcripts.
    Uses the free youtube-transcript-api library (no API key required).
    """
    if context.req.method != 'POST':
        return context.res.json({"error": "Only POST method is allowed"}, 405)

    try:
        body = context.req.body
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = body
            
        video_id = data.get("videoId")

        if not video_id:
            return context.res.json({"error": "videoId is required"}, 400)

        lang = data.get("lang")
        ytt_api = YouTubeTranscriptApi()

        # List available transcripts
        available_languages = []
        try:
            transcript_list = ytt_api.list(video_id)
            for t in transcript_list:
                available_languages.append(t.language_code)
        except Exception:
            pass

        # Determine languages to try
        languages_to_try = []
        if lang:
            languages_to_try.append(lang)
        languages_to_try.append("en")
        for al in available_languages:
            if al not in languages_to_try:
                languages_to_try.append(al)

        # Try to fetch transcript
        last_error = None
        for try_lang in languages_to_try:
            try:
                fetched = ytt_api.fetch(video_id, languages=[try_lang])
                segments = [
                    {
                        "text": snippet.text,
                        "start": snippet.start,
                        "duration": snippet.duration,
                    }
                    for snippet in fetched
                ]

                return context.res.json(
                    {
                        "segments": segments,
                        "language": try_lang,
                        "availableLanguages": available_languages
                        if available_languages
                        else [try_lang],
                    }
                )
            except NoTranscriptFound:
                last_error = f"No transcript found for language: {try_lang}"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        # Fallback to any available
        try:
            transcript_list = ytt_api.list(video_id)
            for t in transcript_list:
                fetched = t.fetch()
                segments = [
                    {
                        "text": snippet.text,
                        "start": snippet.start,
                        "duration": snippet.duration,
                    }
                    for snippet in fetched
                ]
                return context.res.json(
                    {
                        "segments": segments,
                        "language": t.language_code,
                        "availableLanguages": available_languages
                        if available_languages
                        else [t.language_code],
                    }
                )
        except Exception:
            pass

        return context.res.json(
            {
                "error": last_error or "No transcript available for this video",
                "segments": None,
            },
            404
        )

    except TranscriptsDisabled:
        return context.res.json({"error": "Transcripts are disabled", "segments": None}, 404)
    except VideoUnavailable:
        return context.res.json({"error": "Video is unavailable", "segments": None}, 404)
    except Exception as e:
        context.error(str(e))
        return context.res.json({"error": str(e), "segments": None}, 500)
