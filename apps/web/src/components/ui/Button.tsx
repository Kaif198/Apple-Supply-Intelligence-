import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Button — Apple-style pill with spring easing.
 *
 * `default` is the primary action (accent blue), `outline` a hairline
 * alternative, `ghost` hover-only, `subtle` elevated chip, and
 * `destructive` for confirmations.
 */

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-full font-medium transition-all duration-300 ease-spring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-accent text-accent-foreground hover:bg-accent-muted",
        outline:
          "border border-border-subtle bg-transparent text-fg hover:border-border-strong hover:bg-bg-raised",
        ghost:
          "text-fg-muted hover:bg-bg-raised hover:text-fg",
        subtle:
          "bg-bg-raised text-fg hover:bg-bg-inset",
        destructive:
          "bg-signal-neg/90 text-white hover:bg-signal-neg",
      },
      size: {
        sm: "h-7 px-3 text-xs",
        md: "h-9 px-4 text-sm",
        lg: "h-11 px-6 text-base",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "outline",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Component = asChild ? Slot : "button";
    return (
      <Component
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
