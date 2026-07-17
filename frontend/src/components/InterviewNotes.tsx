import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getNotes, addNote, updateNote, deleteNote } from '../services/api';

interface InterviewNotesProps {
  applicationId: string;
}

export const InterviewNotes: React.FC<InterviewNotesProps> = ({ applicationId }) => {
  const queryClient = useQueryClient();
  const [newNote, setNewNote] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const { data: notes = [], isLoading } = useQuery({
    queryKey: ['notes', applicationId],
    queryFn: () => getNotes(applicationId),
  });

  const addMutation = useMutation({
    mutationFn: (content: string) => addNote(applicationId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', applicationId] });
      setNewNote('');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) => updateNote(id, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', applicationId] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteNote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', applicationId] });
    },
  });

  const handleAdd = () => {
    if (newNote.trim()) {
      addMutation.mutate(newNote);
    }
  };

  const handleUpdate = (id: string) => {
    if (editContent.trim()) {
      updateMutation.mutate({ id, content: editContent });
    }
  };

  if (isLoading) {
    return <div className="animate-pulse space-y-4">
      <div className="h-20 bg-gray-100 rounded-xl" />
      <div className="h-20 bg-gray-100 rounded-xl" />
    </div>;
  }

  return (
    <div className="space-y-6">
      {/* Add new note */}
      <div className="bg-gray-50 p-4 rounded-2xl border border-gray-100">
        <textarea
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          placeholder="Add a note (e.g., recruiter name, interview questions, follow-up items)..."
          className="w-full bg-white border border-gray-200 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none resize-none min-h-[100px]"
        />
        <div className="flex justify-end mt-2">
          <button
            onClick={handleAdd}
            disabled={!newNote.trim() || addMutation.isPending}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition-colors disabled:opacity-50"
          >
            {addMutation.isPending ? 'Saving...' : 'Add Note'}
          </button>
        </div>
      </div>

      {/* Note List */}
      <div className="space-y-4">
        {notes.length === 0 ? (
          <p className="text-sm text-gray-500 italic text-center py-4">No notes added yet.</p>
        ) : (
          notes.map((note) => (
            <div key={note.id} className="bg-white p-4 rounded-xl border border-gray-100 shadow-xs relative group">
              {editingId === note.id ? (
                <div className="space-y-3">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-500/20 outline-none resize-none min-h-[80px]"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleUpdate(note.id)}
                      disabled={updateMutation.isPending}
                      className="px-3 py-1 bg-indigo-600 text-white text-xs font-medium rounded-md"
                    >
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{note.content}</p>
                  <div className="flex justify-between items-center mt-3 pt-3 border-t border-gray-50">
                    <span className="text-[10px] text-gray-400 font-medium">
                      {new Date(note.updated_at || note.created_at).toLocaleString()}
                    </span>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                      <button
                        onClick={() => {
                          setEditingId(note.id);
                          setEditContent(note.content);
                        }}
                        className="text-[10px] text-indigo-600 font-semibold hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Delete this note?')) deleteMutation.mutate(note.id);
                        }}
                        className="text-[10px] text-rose-500 font-semibold hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
