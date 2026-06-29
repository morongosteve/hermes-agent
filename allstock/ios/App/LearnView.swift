// LearnView.swift — read the analog-film knowledge base.
//
// Bundle the 15 Markdown notes from allstock/src/allstock/data/knowledge into
// the app target as a "knowledge" folder reference (see ../README.md), and this
// view lists and renders them. The notes are the project's grounded film science.

import SwiftUI

struct KnowledgeNote: Identifiable {
    let id: String          // slug (file stem)
    let title: String
    let body: String
}

enum Knowledge {
    static func load() -> [KnowledgeNote] {
        let urls = Bundle.main.urls(forResourcesWithExtension: "md", subdirectory: "knowledge")
            ?? Bundle.main.urls(forResourcesWithExtension: "md", subdirectory: nil) ?? []
        return urls.sorted { $0.lastPathComponent < $1.lastPathComponent }.compactMap { url in
            guard let body = try? String(contentsOf: url, encoding: .utf8) else { return nil }
            let slug = url.deletingPathExtension().lastPathComponent
            let title = body.split(separator: "\n").first { $0.hasPrefix("# ") }
                .map { String($0.dropFirst(2)) } ?? slug
            return KnowledgeNote(id: slug, title: title, body: body)
        }
    }
}

struct LearnView: View {
    @State private var notes: [KnowledgeNote] = []
    var body: some View {
        NavigationStack {
            Group {
                if notes.isEmpty {
                    ContentUnavailableView("No notes bundled",
                        systemImage: "book.closed",
                        description: Text("Add the 'knowledge' folder of .md files to the app target."))
                } else {
                    List(notes) { note in
                        NavigationLink(note.title) { NoteView(note: note) }
                    }
                }
            }
            .navigationTitle("Learn")
        }
        .onAppear { if notes.isEmpty { notes = Knowledge.load() } }
    }
}

struct NoteView: View {
    let note: KnowledgeNote
    var body: some View {
        ScrollView {
            // Lightweight render: paragraph-by-paragraph AttributedString markdown.
            VStack(alignment: .leading, spacing: 10) {
                ForEach(Array(note.body.components(separatedBy: "\n\n").enumerated()), id: \.offset) { _, para in
                    Text((try? AttributedString(markdown: para,
                        options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))) ?? AttributedString(para))
                        .font(.callout)
                }
            }
            .padding()
        }
        .navigationTitle(note.title)
        .navigationBarTitleDisplayMode(.inline)
    }
}
