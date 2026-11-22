# Author: Jingyu Huang (CNetID: jyhuang28).
"""Keyed fixed-template questions with read-back across the channel/database gap."""
from __future__ import annotations

import channel
from sandbox import course, execution

DISCLOSURE = "An automated agent wrote this message. Contact course staff for human help."


def clarification_text(options):
    return "Which course topic is your question about? Reply with one of: " + ", ".join(options) + ".\n\n" + DISCLOSURE


def confirm(key):
    item = execution.outbox(key)
    if item is None:
        return None
    matches = [message for message in channel.messages(item["thread_id"])
               if message.id > item["since_id"] and message.sender == channel.AGENT
               and message.text == item["body"] and message.session_id == item["run_key"].rsplit(":", 1)[0]]
    if len(matches) > 1:
        raise RuntimeError("More than one matching send; staff must inspect this thread.")
    if not matches:
        return None
    message = matches[0]
    execution.confirm_send(key, message.id)
    return {"message": {"id": message.id, "thread_id": message.thread_id, "body": message.text}}


def ask(question_id, options, key, run_key):
    if not options or len(options) > 6 or any(not course.materials(topic) for topic in options):
        raise ValueError("Choose 1..6 existing public course topics.")
    body = clarification_text(options)
    messages = channel.messages(question_id)
    execution.prepare_send(key, run_key, question_id, body, max((m.id for m in messages), default=0))
    previous = confirm(key)
    if previous:
        return previous
    # Run ownership prevents concurrent replay of this cross-database write.
    message = channel.send(question_id, body)
    execution.confirm_send(key, message.id)
    return {"message": {"id": message.id, "thread_id": question_id, "body": body}}
