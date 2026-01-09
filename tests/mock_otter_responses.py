def get_mock_meetings():
    return [
        {
            'id': 'meeting_1',
            'title': 'Team Sync',
            'date': '2023-01-01',
            'time': '10:00 AM'
        },
        {
            'id': 'meeting_2',
            'title': 'Project Update',
            'date': '2023-01-02',
            'time': '2:00 PM'
        }
    ]

def get_mock_transcript(meeting_id):
    transcripts = {
        'meeting_1': "This is the transcript for meeting 1.",
        'meeting_2': "This is the transcript for meeting 2."
    }
    return transcripts.get(meeting_id, "")

def get_mock_summary(meeting_id):
    summaries = {
        'meeting_1': "Summary for meeting 1.",
        'meeting_2': "Summary for meeting 2."
    }
    return summaries.get(meeting_id, "")

def get_mock_insights(meeting_id):
    insights = {
        'meeting_1': "Insights for meeting 1.",
        'meeting_2': "Insights for meeting 2."
    }
    return insights.get(meeting_id, "")

def get_mock_action_items(meeting_id):
    action_items = {
        'meeting_1': [
            {'text': "Follow up with client", 'owner': "Alice"},
            {'text': "Prepare report", 'owner': "Bob"}
        ],
        'meeting_2': [
            {'text': "Schedule next meeting", 'owner': "Charlie"}
        ]
    }
    return action_items.get(meeting_id, []) 