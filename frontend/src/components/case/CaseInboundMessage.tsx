import { Card } from "../Card";

interface CaseInboundMessageProps {
  body: string;
}

export function CaseInboundMessage({ body }: CaseInboundMessageProps) {
  return (
    <Card title="Bejovo uzenet">
      <div
        className="text-[12px] leading-relaxed bg-[#FbFdfd] border border-one-line rounded-md p-3"
        dangerouslySetInnerHTML={{ __html: body.replace(/\n/g, "<br>") }}
      />
    </Card>
  );
}
