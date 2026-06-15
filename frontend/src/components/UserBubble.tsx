interface UserBubbleProps {
  content: string;
}

export function UserBubble({ content }: UserBubbleProps) {
  return (
    <div className="flex justify-end px-4 py-1">
      <div className="max-w-[75%]">
        <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed shadow-lg">
          {content}
        </div>
      </div>
    </div>
  );
}
