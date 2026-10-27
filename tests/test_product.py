from unittest import mock
from fastapi.testclient import TestClient
import channel
from app.main import app
from harness import runtime
from sandbox import course, seed
from tests.support import ScratchTest


class ProductTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset();seed.seed(None)
        self.client=TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        super().tearDown()

    def test_manual_draft_review_send_and_duplicate_post(self):
        body=course.record("document","SYN-DOC-deadline")["answer"]
        response=self.client.post("/course/draft",data={"question_id":"SYN-Q-deadline","body":body,"sources":"SYN-DOC-deadline"})
        self.assertEqual(response.status_code,200)
        draft=course.effects()[0]
        self.assertEqual(draft["stamp"],"manual")
        self.assertFalse([m for m in channel.messages("SYN-Q-deadline") if m.sender=="operator"])
        self.client.post("/course/send",data={"effect_id":draft["id"]})
        self.assertEqual(course.effect(draft["id"])["status"],"pending")
        for _ in range(2):
            self.client.post("/course/send",data={"effect_id":draft["id"],"reviewed":"yes"})
        sent=[m for m in channel.messages("SYN-Q-deadline") if m.sender=="operator"]
        self.assertEqual(len(sent),1)
        self.assertEqual(sent[0].text,body)
        self.assertEqual(course.effect(draft["id"])["status"],"sent")

    def test_flags_clear_reopen_and_draft_discard_restore(self):
        self.client.post("/course/flag",data={"question_id":"SYN-Q-deadline","reason":"missing_information"})
        flag=course.effects()[0]
        self.assertEqual(flag["stamp"],"manual")
        for status in ("cleared","open"):
            self.client.post("/course/status",data={"effect_id":flag["id"],"status":status,"note":"Staff reviewed"})
            self.assertEqual(course.effect(flag["id"])["status"],status)
        self.client.post("/course/draft",data={"question_id":"SYN-Q-concept","body":"Manual explanation"})
        reply=next(x for x in course.effects() if x["kind"]=="reply")
        for status in ("discarded","pending"):
            self.client.post("/course/status",data={"effect_id":reply["id"],"status":status})
            self.assertEqual(course.effect(reply["id"])["status"],status)

    def test_uncertain_send_is_held_and_not_retried(self):
        draft=course.manual_draft("SYN-Q-deadline","Manual reply",[])
        with mock.patch("channel.send",side_effect=TimeoutError("delivery unknown")) as send:
            self.client.post("/course/send",data={"effect_id":draft["id"],"reviewed":"yes"})
            self.client.post("/course/send",data={"effect_id":draft["id"],"reviewed":"yes"})
        self.assertEqual(send.call_count,1)
        self.assertEqual(course.effect(draft["id"])["status"],"uncertain")

    def test_console_runs_workflow_and_source_text_is_escaped(self):
        self.client.post("/console/course-demo/turn",data={"text":"Process SYN-Q-deadline"})
        self.assertEqual(course.effects()[0]["stamp"],"course-demo")
        channel.receive("SYN-Q-deadline","<script>alert('bad')</script>",sender="SYN-STUDENT-001")
        page=self.client.get("/").text
        self.assertNotIn("<script>alert('bad')</script>",page)
        self.assertIn("&lt;script&gt;",page)
