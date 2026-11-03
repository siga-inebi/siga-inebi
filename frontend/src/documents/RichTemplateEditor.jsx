import { useRef, useState } from "react";

import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";

const blockText = (block) => block.content?.[0]?.text ?? "";
const blockMarks = (block) => block.content?.[0]?.marks ?? [];

export function RichTemplateEditor({ disabled, value, onChange, insertTag }) {
  const [active, setActive] = useState(0);
  const refs = useRef([]);
  const blocks = value?.content ?? [];
  const update = (index, patch) => {
    const content = blocks.map((block, position) =>
      position === index ? { ...block, ...patch } : block
    );
    onChange({ ...value, content });
  };
  const updateText = (index, text, marks = blockMarks(blocks[index])) =>
    update(index, {
      content: [{ type: "text", text, ...(marks.length ? { marks } : {}) }],
    });
  const applyTag = (tag) => {
    const input = refs.current[active];
    const text = blockText(blocks[active]);
    const start = input?.selectionStart ?? text.length;
    const end = input?.selectionEnd ?? start;
    updateText(active, `${text.slice(0, start)}{{${tag}}}${text.slice(end)}`);
    requestAnimationFrame(() => input?.focus());
  };
  if (insertTag) insertTag.current = applyTag;

  return (
    <Stack gap={1.5}>
      {blocks.map((block, index) => {
        const marks = blockMarks(block);
        return (
          <Box
            key={index}
            sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}
          >
            <Stack direction={{ xs: "column", sm: "row" }} gap={1} mb={1}>
              <TextField
                select
                size="small"
                label="Bloque"
                value={block.type}
                disabled={disabled}
                onChange={(event) =>
                  update(index, {
                    type: event.target.value,
                    ...(event.target.value === "heading" ? { level: 2 } : {}),
                  })
                }
              >
                <MenuItem value="paragraph">Párrafo</MenuItem>
                <MenuItem value="heading">Encabezado</MenuItem>
              </TextField>
              <ToggleButtonGroup
                exclusive
                size="small"
                value={block.align ?? "left"}
                onChange={(_, align) => align && update(index, { align })}
              >
                {["left", "center", "right", "justify"].map((align) => (
                  <ToggleButton key={align} value={align}>
                    {align.slice(0, 1).toUpperCase()}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
              <ToggleButtonGroup
                size="small"
                value={marks}
                onChange={(_, next) =>
                  updateText(index, blockText(block), next)
                }
              >
                <ToggleButton value="bold">
                  <strong>N</strong>
                </ToggleButton>
                <ToggleButton value="italic">
                  <em>K</em>
                </ToggleButton>
                <ToggleButton value="underline">
                  <u>S</u>
                </ToggleButton>
              </ToggleButtonGroup>
              <IconButton
                aria-label="Eliminar bloque"
                disabled={disabled || blocks.length === 1}
                onClick={() =>
                  onChange({
                    ...value,
                    content: blocks.filter((_, position) => position !== index),
                  })
                }
              >
                <DeleteOutlineIcon />
              </IconButton>
            </Stack>
            <TextField
              fullWidth
              multiline
              minRows={block.type === "heading" ? 1 : 3}
              inputRef={(node) => {
                refs.current[index] = node;
              }}
              disabled={disabled}
              label={
                block.type === "heading"
                  ? "Encabezado"
                  : index === 0
                    ? "Contenido de la plantilla"
                    : "Texto"
              }
              value={blockText(block)}
              onFocus={() => setActive(index)}
              onChange={(event) => updateText(index, event.target.value)}
            />
          </Box>
        );
      })}
      <Button
        startIcon={<AddIcon />}
        disabled={disabled}
        onClick={() =>
          onChange({
            ...value,
            content: [
              ...blocks,
              {
                type: "paragraph",
                align: "left",
                content: [{ type: "text", text: "" }],
              },
            ],
          })
        }
      >
        Agregar bloque
      </Button>
    </Stack>
  );
}
