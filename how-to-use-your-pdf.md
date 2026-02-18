# How to Talk With Your Reference Material

## Quick Start

Your backend is already running with **171 documents** indexed in Qdrant! Here's how to interact with them:

---

## 🎯 Method 1: Voice Questions (Recommended)

### Steps:
1. **Open the app**: Navigate to `http://localhost:3000` in your browser
2. **Grant microphone permission** when prompted
3. **Hold the recorder button** (looks like a microphone icon)
4. **Ask your question** clearly:
   - "What is [concept from your PDF]?"
   - "Explain [topic] from my notes"
   - "How does [concept A] relate to [concept B]?"
5. **Release the button** when done speaking
6. **Wait for response**:
   - Your question appears as a student message
   - Tutor thinks (loading dots)
   - Tutor's Socratic response appears
   - Audio plays automatically (Edge TTS Neural Voice)

### What Happens Behind the Scenes:
```
Your voice → Groq Whisper (transcribes) → LangGraph (routes)
→ RAG node (searches Qdrant for relevant PDF chunks)
→ Socratic node (Groq Llama 3 generates response)
→ Edge TTS (speaks answer) → You hear it!
```

---

## 💬 Method 2: Text Questions

### Steps:
1. **Open the app**: `http://localhost:3000`
2. **Type your question** in the text input at the bottom
3. **Click "Send"** or press Enter
4. **Same flow as voice**, but no microphone needed

### Advantages:
- More precise questions
- Better for complex queries
- No audio processing delay

---

## 🔍 How to Verify RAG is Working

### Browser DevTools (F12):
1. Open **Console** tab
2. Ask a question about your PDF
3. Look for transcript event:
   ```json
   {
     "from": "tutor",
     "text": "Let's explore that concept...",
     "rag_sources_used": true,      ← Should be true!
     "rag_context_count": 3          ← Number of PDF chunks used
   }
   ```

### Backend Terminal Logs:
Look for these messages after asking:
```
RAG search completed, results_count: 3
Retrieved context: [text from your PDF]
Response sent with RAG info, rag_sources_used: true
```

---

## 📚 Understanding RAG Behavior

### When RAG Activates:
- ✅ You ask about specific content in your PDF
- ✅ You mention concepts/terms from your material
- ✅ You request explanations of uploaded topics
- ✅ You ask "Quiz me" (uses deficit areas from memory)

### When RAG May Not Activate:
- ❌ General greeting ("Hello", "How are you?")
- ❌ Questions completely unrelated to your PDF
- ❌ Meta questions about the system itself
- ❌ First turn before establishing context

### Why RAG Might Not Find Content:
1. **Different terminology**: PDF uses "cellular respiration", you ask about "cell breathing"
2. **User ID mismatch**: Check browser localStorage for `user_id`
3. **Empty collection**: Verify upload succeeded
4. **Query too vague**: Be specific about what you want to know

---

## 🎓 Socratic Tutoring Style

The tutor doesn't just answer—it **guides you to discover**:

### Example Interaction:

**You**: "What is photosynthesis?"

**Tutor (without RAG)**: "Let's start with the basics. What do you know about how plants get their energy?"

**Tutor (with RAG - using your PDF)**:  
"I see you've studied photosynthesis in your notes. Let's explore this deeper. Your material mentions the light-dependent reactions. Can you describe what happens to water molecules in that stage?"

### Notice the Difference:
- **With RAG**: References your material, asks follow-up based on what you've learned
- **Without RAG**: Starts from scratch, general educational approach

---

## 🧪 Testing RAG Step-by-Step

### Test 1: Direct Question
```
You: "What are the main topics in my notes?"
Expected: Tutor lists/discusses actual topics from your PDF
DevTools: rag_sources_used: true, rag_context_count: 5+
```

### Test 2: Concept Explanation
```
You: "Explain [specific term from your PDF]"
Expected: Tutor asks questions to guide you through the concept
DevTools: rag_sources_used: true, rag_context_count: 2-4
```

### Test 3: Quiz Mode
```
You: "Quiz me"
Expected: Tutor creates questions from topics in your PDF
DevTools: rag_sources_used: true (uses memory + RAG)
```

---

## 🔧 Troubleshooting

### "RAG not finding my content"

#### Check User ID:
```bash
# In browser console:
localStorage.getItem('user_id')
# Should return something like: "abc123-def456-..."
```

#### Check Qdrant:
```bash
# Terminal:
curl -s http://localhost:6333/collections/agora_notes | python3 -m json.tool

# Should show:
{
  "result": {
    "status": "green",
    "points_count": 171,  ← Your documents
    ...
  }
}
```

#### Check Upload Worked:
If points_count is 0, your PDF wasn't ingested. Re-upload:
```bash
curl -X POST http://localhost:8000/api/materials/upload \
  -F "file=@your_notes.pdf" \
  -F "user_id=$(your_user_id_here)" \
  -F "course_id=default"
```

---

### "Tutor responds but doesn't use my material"

This could be:
1. **Routing decision**: LangGraph may decide RAG isn't needed for that question
2. **Low relevance scores**: Your question doesn't semantically match PDF content
3. **General knowledge question**: System uses Groq/Llama's knowledge instead

**Solution**: Be more specific about referencing your notes:
- ❌ "Tell me about biology"
- ✅ "Based on my notes about cellular respiration, explain..."

---

### "Audio doesn't play"

Check:
1. **Browser permissions**: Allow audio playback
2. **Volume**: System volume not muted
3. **Backend logs**: Look for "Edge TTS synthesis completed"
4. **Console errors**: Check for WebSocket audio event errors

---

## 📊 RAG Performance Tips

### Better Questions = Better RAG:
```
❌ Vague: "Tell me stuff"
✅ Specific: "What does my PDF say about mitochondria?"

❌ Too broad: "Explain everything"
✅ Focused: "Compare the two theories mentioned in section 3"

❌ Implicit: "What should I know?"
✅ Explicit: "Quiz me on the equations from my physics notes"
```

### Optimize Your PDFs:
- **Clear headings**: Helps chunking
- **Concise sections**: Better retrieval
- **Key terms defined**: Improves semantic matching
- **Structured content**: Easier to reference

---

## 🎯 Expected User Experience

### Perfect RAG Flow:
1. You ask: "Explain concept X from my notes"
2. **Instant feedback**: Your message appears
3. **Loading state**: Tutor thinking (2-5 seconds)
4. **Response appears**: Tutor's Socratic question
5. **Audio plays**: Edge TTS speaks the response
6. **Console shows**: `rag_sources_used: true, rag_context_count: 3`
7. **Backend logs**: "Retrieved context: [snippet from your PDF]"

### Session Context:
- Each conversation remembers previous exchanges
- Memory node tracks what you've struggled with
- Frustration monitor adjusts teaching style
- Quiz mode uses deficit areas from memory

---

## 🚀 Advanced Usage

### Combining Memory + RAG:
```
Turn 1: "What is X?" (uses RAG)
Turn 2: "I don't understand" (tutor notes frustration)
Turn 3: Tutor simplifies, references your earlier question
Turn 4: "Quiz me" (uses memory of struggled topics + RAG)
```

### Multi-Document RAG:
If you've uploaded multiple PDFs:
- RAG searches ALL documents with your `user_id`
- Can optionally filter by `course_id`
- Retrieves top 5 most relevant chunks across all materials

---

## 📝 Summary Checklist

- [ ] Backend running on http://localhost:8000 (health check passes)
- [ ] Qdrant has 171+ documents indexed
- [ ] Frontend running on http://localhost:3000
- [ ] Microphone permission granted
- [ ] Asked specific question about PDF content
- [ ] Checked DevTools console for `rag_sources_used: true`
- [ ] Backend logs show "RAG search completed"
- [ ] Tutor response references your material
- [ ] Audio plays via Edge TTS

**If all checked**: RAG is working perfectly! 🎉

---

## 💡 Pro Tips

1. **Start specific**: "According to my notes on [topic]..."
2. **Use exact terms**: If your PDF says "mitosis", use "mitosis" not "cell division"
3. **Reference sections**: "In the chapter about..."
4. **Ask for synthesis**: "How do concepts A and B from my notes relate?"
5. **Request elaboration**: "My notes mention X. Can you help me understand why?"

---

**Need Help?**
- Check `CHANGES_SUMMARY.md` for system overview
- Review backend logs for detailed trace
- Verify health: `curl http://localhost:8000/health`
- Test Qdrant: `curl http://localhost:6333/collections/agora_notes`

**Happy learning! 📚✨**
