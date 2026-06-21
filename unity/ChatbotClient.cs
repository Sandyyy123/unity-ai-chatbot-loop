// ChatbotClient.cs
// Drop this MonoBehaviour on a GameObject in your Unity3D scene. It talks to
// the Python conversation-loop service (app.py) over HTTP. All the loop state,
// memory and model calls live server-side - Unity just sends text and renders
// the reply. Coroutine-based so it never blocks the game thread.
//
// Usage in your dialogue code:
//     chatbotClient.Send("Hello", reply => dialogueLabel.text = reply);

using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

public class ChatbotClient : MonoBehaviour
{
    [Tooltip("Base URL of the Python loop service, e.g. http://localhost:8000")]
    public string serverUrl = "http://localhost:8000";

    [Tooltip("Stable id per player/NPC so the server keeps that conversation's state.")]
    public string sessionId = "player-1";

    [Tooltip("Optional character the bot should play.")]
    public string persona = "a gruff but kind tavern keeper";

    [Serializable]
    private class ChatRequest
    {
        public string session_id;
        public string message;
        public string persona;
    }

    [Serializable]
    private class ChatResponse
    {
        public string reply;
        public int turns;
    }

    [Serializable]
    private class RememberRequest
    {
        public string session_id;
        public string key;
        public string value;
    }

    /// <summary>Send a player message; onReply fires on the main thread with the bot's text.</summary>
    public void Send(string message, Action<string> onReply, Action<string> onError = null)
    {
        StartCoroutine(SendRoutine(message, onReply, onError));
    }

    /// <summary>Push a world fact (player name, quest state) into the bot's memory.</summary>
    public void Remember(string key, string value, Action onDone = null)
    {
        StartCoroutine(RememberRoutine(key, value, onDone));
    }

    private IEnumerator SendRoutine(string message, Action<string> onReply, Action<string> onError)
    {
        var payload = new ChatRequest { session_id = sessionId, message = message, persona = persona };
        string json = JsonUtility.ToJson(payload);

        using (var req = new UnityWebRequest($"{serverUrl}/chat", "POST"))
        {
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");

            yield return req.SendWebRequest();

            if (req.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke(req.error);
                Debug.LogWarning($"[ChatbotClient] {req.error}");
                yield break;
            }

            var resp = JsonUtility.FromJson<ChatResponse>(req.downloadHandler.text);
            onReply?.Invoke(resp.reply);
        }
    }

    private IEnumerator RememberRoutine(string key, string value, Action onDone)
    {
        var payload = new RememberRequest { session_id = sessionId, key = key, value = value };
        string json = JsonUtility.ToJson(payload);

        using (var req = new UnityWebRequest($"{serverUrl}/remember", "POST"))
        {
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");

            yield return req.SendWebRequest();
            onDone?.Invoke();
        }
    }
}
